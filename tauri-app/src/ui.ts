/**
 * UI 组件模块
 * 聊天窗口/右键菜单/系统托盘
 */

export interface ChatWindowOptions {
    containerId: string;
    onSend?: (message: string) => void;
    onClose?: () => void;
}

export class ChatWindowUI {
    private container: HTMLElement | null = null;
    private messagesEl: HTMLElement | null = null;
    private inputEl: HTMLTextAreaElement | null = null;
    private onSend?: (message: string) => void;
    private onClose?: () => void;

    constructor(options: ChatWindowOptions) {
        this.onSend = options.onSend;
        this.onClose = options.onClose;
        this.init(options.containerId);
    }

    private init(containerId: string) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.messagesEl = this.container.querySelector('.chat-messages');
        this.inputEl = this.container.querySelector('#chat-input');

        // 绑定发送按钮
        const sendBtn = this.container.querySelector('#send-btn');
        sendBtn?.addEventListener('click', () => this.send());

        // 绑定关闭按钮
        const closeBtn = this.container.querySelector('.close-btn');
        closeBtn?.addEventListener('click', () => this.close());

        // Enter 发送
        this.inputEl?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        });
    }

    public show() {
        this.container?.classList.add('visible');
        this.inputEl?.focus();
    }

    public hide() {
        this.container?.classList.remove('visible');
    }

    public toggle() {
        if (this.container?.classList.contains('visible')) {
            this.hide();
        } else {
            this.show();
        }
    }

    public addMessage(role: string, content: string) {
        if (!this.messagesEl) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        msgDiv.appendChild(contentDiv);
        this.messagesEl.appendChild(msgDiv);

        // 滚动到底部
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }

    private send() {
        if (!this.inputEl) return;
        const text = this.inputEl.value.trim();
        if (!text) return;

        this.inputEl.value = '';
        this.onSend?.(text);
    }

    private close() {
        this.hide();
        this.onClose?.();
    }
}

// 右键菜单
export class ContextMenu {
    private menu: HTMLElement | null = null;
    private items: Array<{ label: string; onClick: () => void }> = [];

    constructor() {
        this.init();
    }

    private init() {
        this.menu = document.createElement('div');
        this.menu.id = 'context-menu';
        this.menu.innerHTML = `
            <button data-action="chat">💬 聊天</button>
            <button data-action="character">🎭 切换角色</button>
            <div class="separator"></div>
            <button data-action="hide">🙈 隐藏</button>
            <button data-action="settings">⚙️ 设置</button>
            <div class="separator"></div>
            <button data-action="quit">❌ 退出</button>
        `;
        document.body.appendChild(this.menu);

        // 绑定点击事件
        this.menu.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            if (target.tagName === 'BUTTON') {
                const action = target.dataset.action;
                this.handleAction(action || '');
            }
        });

        // 点击其他地方关闭
        document.addEventListener('click', (e) => {
            if (!this.menu?.contains(e.target as Node)) {
                this.hide();
            }
        });
    }

    public show(x: number, y: number) {
        if (this.menu) {
            this.menu.style.left = x + 'px';
            this.menu.style.top = y + 'px';
            this.menu.classList.add('visible');
        }
    }

    public hide() {
        this.menu?.classList.remove('visible');
    }

    public addItem(label: string, onClick: () => void) {
        this.items.push({ label, onClick });
    }

    private handleAction(action: string) {
        console.log('🎯 Action:', action);
        this.hide();
    }
}
