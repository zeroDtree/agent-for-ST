// 建立 SSE 连接
const serverUrl = "http://localhost:5000";
const sessionId = "default"; // 可以从后端返回的 session_id 动态设置
const es = new EventSource(`${serverUrl}/api/events?session_id=${sessionId}`);

// 监听消息
es.onmessage = (event) => {
	const data = JSON.parse(event.data);
	console.log("收到 SSE 事件:", data);

	// 根据不同事件类型处理
	if (data.type === "connected") {
		console.log("SSE 连接已建立, 会话ID:", data.session_id);
	} else if (data.type === "heartbeat") {
		console.log("收到心跳包");
	} else if (data.type === "confirmation_request") {
		console.log("收到确认请求:", data);
		showConfirmationDialog(data);
	} else {
		console.log("收到未知事件类型:", data.type, data);
	}
};

es.onopen = (event) => {
	console.log("SSE 连接已打开");
};

es.onerror = (err) => {
	console.error("SSE 连接出错:", err);
	console.log("连接状态:", es.readyState);
};

// 弹窗函数
function showConfirmationDialog(eventData) {
	const command = eventData.command || "未知命令";
	const toolName = eventData.tool_name || "未知工具";
	const message = `是否执行${toolName}命令:\n${command}`;

	const confirmed = confirm(message);

	// 发送确认结果到服务器
	fetch(`${serverUrl}/api/confirm-command`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
		},
		body: JSON.stringify({
			session_id: eventData.session_id || sessionId,
			confirmed: confirmed
		})
	})
		.then(res => {
			if (!res.ok) {
				throw new Error(`HTTP错误: ${res.status}`);
			}
			return res.json();
		})
		.then(result => {
			console.log("确认结果:", result);
			if (result.status === "success") {
				console.log(`命令已${confirmed ? '确认' : '拒绝'}执行`);
			} else {
				console.error("确认处理失败:", result.message);
			}
		})
		.catch(err => {
			console.error("确认请求失败:", err);
		});
}

// 添加页面关闭时的清理
window.addEventListener('beforeunload', () => {
	if (es) {
		es.close();
		console.log("SSE 连接已关闭");
	}
});

// 定期检查连接状态
setInterval(() => {
	if (es.readyState === EventSource.CLOSED) {
		console.warn("SSE 连接已断开，需要重新连接");
	}
}, 5000);