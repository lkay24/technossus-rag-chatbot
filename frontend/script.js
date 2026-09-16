const API_URL = "http://localhost:8000/chat";

const heroSection = document.getElementById("heroSection");
const chatSection = document.getElementById("chatSection");
const chatArea = document.getElementById("chatArea");
const form = document.getElementById("composerForm");
const input = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");

let chatStarted = false;

function activateChatView() {
    if (chatStarted) return;
    chatStarted = true;
    heroSection.style.display = "none";
    chatSection.classList.add("active");
}

function formatTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `
        <div class="bubble">${text.replace(/</g, "&lt;")}</div>
        <div class="msg-meta"><span class="timestamp">${formatTime()}</span></div>
    `;
    chatArea.appendChild(row);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function appendBotMessage(markdownText, sources) {
    const row = document.createElement("div");
    row.className = "message-row bot";

    const html = window.marked ? marked.parse(markdownText) : markdownText;

    let sourceHtml = "";
    if (sources && sources.length > 0) {
        sourceHtml = sources.slice(0, 3).map(url => {
            const label = url.split("/").filter(Boolean).pop() || "Home";
            const niceLabel = label.replace(/-/g, " ");
            return `<a class="source-badge" href="${url}" target="_blank" rel="noopener">Source: ${niceLabel}</a>`;
        }).join(" ");
    }

    row.innerHTML = `
        <div class="bubble">${html}</div>
        <div class="msg-meta">
            <span class="timestamp">${formatTime()}</span>
            <button class="copy-btn" type="button">Copy</button>
        </div>
        ${sourceHtml}
    `;

    const copyBtn = row.querySelector(".copy-btn");
    copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(markdownText);
        copyBtn.textContent = "Copied";
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
    });

    chatArea.appendChild(row);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function showLoading() {
    const row = document.createElement("div");
    row.className = "loading-row";
    row.id = "loadingRow";
    row.innerHTML = `
        <div class="loading-dots"><span></span><span></span><span></span></div>
        <span>Searching website knowledge...</span>
    `;
    chatArea.appendChild(row);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function hideLoading() {
    const el = document.getElementById("loadingRow");
    if (el) el.remove();
}

async function sendQuestion(question) {
    activateChatView();
    appendUserMessage(question);
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    showLoading();

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        if (!response.ok) throw new Error(`Server returned ${response.status}`);

        const data = await response.json();
        hideLoading();
        appendBotMessage(data.answer, data.sources);
    } catch (err) {
        hideLoading();
        appendBotMessage("I couldn't reach the assistant. Make sure the backend server is running.", []);
        console.error(err);
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

form.addEventListener("submit", (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    sendQuestion(question);
});

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
});

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
    }
});

document.querySelectorAll(".suggestion-card").forEach(card => {
    card.addEventListener("click", () => {
        const prompt = card.getAttribute("data-prompt");
        sendQuestion(prompt);
    });
});