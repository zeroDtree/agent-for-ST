// Establish SSE connection
const serverUrl = "http://localhost:5000";
const sessionId = "default"; // Can be dynamically set from session_id returned by backend
const es = new EventSource(`${serverUrl}/api/events?session_id=${sessionId}`);

// Listen for messages
es.onmessage = (event) => {
	const data = JSON.parse(event.data);
	console.log("Received SSE event:", data);

	// Handle different event types
	if (data.type === "connected") {
		console.log("SSE connection established, session ID:", data.session_id);
	} else if (data.type === "heartbeat") {
		console.log("Received heartbeat");
	} else if (data.type === "confirmation_request") {
		console.log("Received confirmation request:", data);
		showConfirmationDialog(data);
	} else {
		console.log("Received unknown event type:", data.type, data);
	}
};

es.onopen = (event) => {
	console.log("SSE connection opened");
};

es.onerror = (err) => {
	console.error("SSE connection error:", err);
	console.log("Connection state:", es.readyState);
};

// Dialog function
function showConfirmationDialog(eventData) {
	const command = eventData.command || "Unknown command";
	const toolName = eventData.tool_name || "Unknown tool";
	const message = `Execute ${toolName} command:\n${command}?`;

	const confirmed = confirm(message);

	// Send confirmation result to server
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
				throw new Error(`HTTP error: ${res.status}`);
			}
			return res.json();
		})
		.then(result => {
			console.log("Confirmation result:", result);
			if (result.status === "success") {
				console.log(`Command ${confirmed ? 'confirmed' : 'rejected'} for execution`);
			} else {
				console.error("Confirmation processing failed:", result.message);
			}
		})
		.catch(err => {
			console.error("Confirmation request failed:", err);
		});
}

// Add cleanup when page closes
window.addEventListener('beforeunload', () => {
	if (es) {
		es.close();
		console.log("SSE connection closed");
	}
});

// Periodically check connection status
setInterval(() => {
	if (es.readyState === EventSource.CLOSED) {
		console.warn("SSE connection disconnected, reconnection needed");
	}
}, 5000);