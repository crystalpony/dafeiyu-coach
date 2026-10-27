import Foundation

/// 极简本地 IPC：UNIX domain socket + 一行一个 JSON。
/// 只接受本机当前用户（socket 权限 0600），不监听任何网络端口。
final class CoachServer {
    enum ServerError: Error, CustomStringConvertible {
        case alreadyRunning
        case pathTooLong
        case socketFailed(Int32)
        case bindFailed(Int32)

        var description: String {
            switch self {
            case .alreadyRunning: return "已有大肥鱼在运行"
            case .pathTooLong: return "socket 路径过长"
            case .socketFailed(let e): return "socket() 失败 errno=\(e)"
            case .bindFailed(let e): return "bind() 失败 errno=\(e)"
            }
        }
    }

    private var listenFD: Int32 = -1
    private var source: DispatchSourceRead?
    private let queue = DispatchQueue(label: "coach.socket", qos: .utility)
    var handler: (([String: Any]) -> [String: Any])?

    deinit { stop() }

    func start() throws {
        Paths.ensureHome()
        let path = Paths.socket.path
        if path.utf8.count >= 100 { throw ServerError.pathTooLong }

        if FileManager.default.fileExists(atPath: path) {
            if isListening(path) { throw ServerError.alreadyRunning }
            unlink(path)
        }

        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { throw ServerError.socketFailed(errno) }
        listenFD = fd

        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        let utf8 = Array(path.utf8)
        withUnsafeMutableBytes(of: &addr.sun_path) { raw in
            raw.copyBytes(from: utf8.prefix(max(0, raw.count - 1)))
        }
        let size = socklen_t(MemoryLayout<sockaddr_un>.size)
        let ok = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, size) }
        }
        guard ok == 0 else {
            close(fd); listenFD = -1
            throw ServerError.bindFailed(errno)
        }
        chmod(path, 0o600)
        guard listen(fd, 16) == 0 else {
            close(fd); listenFD = -1
            throw ServerError.bindFailed(errno)
        }

        let flags = fcntl(fd, F_GETFL, 0)
        _ = fcntl(fd, F_SETFL, flags | O_NONBLOCK)

        let src = DispatchSource.makeReadSource(fileDescriptor: fd, queue: queue)
        src.setEventHandler { [weak self] in self?.acceptAll() }
        src.resume()
        source = src
        logLine("socket listening \(path)")
    }

    func stop() {
        source?.cancel()
        source = nil
        if listenFD >= 0 { close(listenFD); listenFD = -1 }
        unlink(Paths.socket.path)
    }

    private func isListening(_ path: String) -> Bool {
        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { return false }
        defer { close(fd) }
        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        let utf8 = Array(path.utf8)
        withUnsafeMutableBytes(of: &addr.sun_path) { raw in
            raw.copyBytes(from: utf8.prefix(max(0, raw.count - 1)))
        }
        let size = socklen_t(MemoryLayout<sockaddr_un>.size)
        let r = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, size) }
        }
        return r == 0
    }

    private func acceptAll() {
        while true {
            let client = accept(listenFD, nil, nil)
            if client < 0 { break }
            handleClient(client)
        }
    }

    private func handleClient(_ fd: Int32) {
        defer { close(fd) }
        // accept() 在部分 macOS 版本会把非阻塞标志带给客户端；显式恢复阻塞读。
        let fl = fcntl(fd, F_GETFL, 0)
        if fl >= 0 { _ = fcntl(fd, F_SETFL, fl & ~O_NONBLOCK) }
        var noSigPipe: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &noSigPipe, socklen_t(MemoryLayout<Int32>.size))
        var timeout = timeval(tv_sec: 3, tv_usec: 0)
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))

        var buffer = Data()
        var chunk = [UInt8](repeating: 0, count: 8192)
        while buffer.count < 1_048_576 {
            let n = chunk.withUnsafeMutableBytes { raw -> Int in
                guard let base = raw.baseAddress else { return -1 }
                return read(fd, base, raw.count)
            }
            if n <= 0 { break }
            buffer.append(contentsOf: chunk[0..<n])
            if buffer.contains(0x0A) { break }
        }
        let response: [String: Any]
        if buffer.isEmpty {
            response = ["ok": false, "error": "空请求"]
        } else if let obj = try? JSONSerialization.jsonObject(with: buffer) as? [String: Any] {
            let box = Box(obj)
            DispatchQueue.main.sync {
                box.value = self.handler?(obj) ?? ["ok": false, "error": "no handler"]
            }
            response = box.value
        } else {
            response = ["ok": false, "error": "JSON 解析失败"]
        }
        guard var out = try? JSONSerialization.data(withJSONObject: response, options: [.sortedKeys]) else { return }
        out.append(0x0A)
        out.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { return }
            var sent = 0
            while sent < out.count {
                let n = write(fd, base.advanced(by: sent), out.count - sent)
                if n <= 0 { break }
                sent += n
            }
        }
    }

    private final class Box {
        var value: [String: Any]
        init(_ v: [String: Any]) { value = v }
    }
}
