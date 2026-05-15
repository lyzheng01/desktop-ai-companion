/**
 * 聊天客户端模块
 * 处理消息发送/接收，调用后端 AI 接口
 */

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string;
}

export interface ChatConfig {
    apiEndpoint?: string;
    model?: string;
}

export interface MemoryItem {
    id: number;
    content: string;
    category: string;
    importance: number;
    created_at: string;
}

export interface CompanionProfile {
    id: number;
    name: string;
    character_type: string;
    personality_tags: string[];
    interaction_mode: string;
    is_active: boolean;
}

export interface ImportedModelItem {
    id: number;
    name: string;
    model_path: string;
    source: string;
    is_active: boolean;
}

export class ApiRequestError extends Error {
    status: number;
    detail: string | null;

    constructor(message: string, status: number, detail: string | null = null) {
        super(message);
        this.name = 'ApiRequestError';
        this.status = status;
        this.detail = detail;
    }
}

export class ChatClient {
    private messages: ChatMessage[] = [];
    private config: ChatConfig;
    private listeners: Set<(msg: ChatMessage) => void> = new Set();

    constructor(config: ChatConfig = {}) {
        this.config = config;
    }

    // 添加消息监听器
    public onMessage(callback: (msg: ChatMessage) => void) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    // 发送消息
    public async send(content: string): Promise<void> {
        // 添加用户消息
        const userMsg: ChatMessage = {
            role: 'user',
            content,
            timestamp: new Date().toISOString(),
        };
        this.messages.push(userMsg);
        this.notify(userMsg);

        // 调用 AI 接口
        try {
            const response = await this.callAI(content);
            this.notify(response);
        } catch (error) {
            console.error('AI 调用失败:', error);
            const errorMsg: ChatMessage = {
                role: 'assistant',
                content: '抱歉，我遇到了一些问题，请稍后再试。',
            };
            this.notify(errorMsg);
        }
    }

    public async sendAndReturn(content: string): Promise<ChatMessage> {
        const userMsg: ChatMessage = {
            role: 'user',
            content,
            timestamp: new Date().toISOString(),
        };
        this.messages.push(userMsg);

        return this.callAI(content);
    }

    public async loadHistory(limit: number = 20): Promise<ChatMessage[]> {
        const historyEndpoint = this.getEndpointUrl('history');

        const response = await fetch(`${historyEndpoint}?limit=${limit}`);
        if (!response.ok) {
            throw new Error(`History request failed: ${response.status}`);
        }

        const data = await response.json() as ChatMessage[];
        this.messages = Array.isArray(data) ? data : [];

        return this.getHistory(limit);
    }

    public async loadMemory(): Promise<MemoryItem[]> {
        const response = await fetch(this.getEndpointUrl('memory'));
        if (!response.ok) {
            throw new Error(`Memory request failed: ${response.status}`);
        }
        return await response.json() as MemoryItem[];
    }

    public async deleteMemory(memoryId: number): Promise<void> {
        const response = await fetch(`${this.getEndpointUrl('memory')}/${memoryId}`, { method: 'DELETE' });
        if (!response.ok) {
            throw new Error(`Delete memory failed: ${response.status}`);
        }
    }

    public async loadCompanions(): Promise<CompanionProfile[]> {
        const response = await fetch(this.getEndpointUrl('companions'));
        if (!response.ok) {
            throw new Error(`Companions request failed: ${response.status}`);
        }
        return await response.json() as CompanionProfile[];
    }

    public async loadActiveCompanion(): Promise<CompanionProfile | null> {
        const response = await fetch(this.getEndpointUrl('companions-active'));
        if (response.status === 404) {
            return null;
        }
        if (!response.ok) {
            throw new Error(`Active companion request failed: ${response.status}`);
        }
        return await response.json() as CompanionProfile | null;
    }

    public async createCompanion(payload: {
        name: string;
        character_type: string;
        personality_tags: string[];
        interaction_mode: string;
    }): Promise<number> {
        const response = await fetch(this.getEndpointUrl('companions'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            throw await this.buildApiRequestError('Create companion failed', response);
        }
        const data = await response.json() as { id: number };
        return data.id;
    }

    public async activateCompanion(companionId: number): Promise<void> {
        const response = await fetch(`${this.getEndpointUrl('companions')}/${companionId}/activate`, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`Activate companion failed: ${response.status}`);
        }
    }

    public async loadImportedModels(): Promise<ImportedModelItem[]> {
        const response = await fetch(this.getEndpointUrl('models-imported'));
        if (!response.ok) {
            throw new Error(`Imported models request failed: ${response.status}`);
        }
        return await response.json() as ImportedModelItem[];
    }

    public async importModel(payload: { name: string; model_path: string }): Promise<void> {
        const response = await fetch(this.getEndpointUrl('models-imported'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            throw await this.buildApiRequestError('Import model failed', response);
        }
    }

    // 调用 AI 接口
    private async callAI(userMessage: string): Promise<ChatMessage> {
        // 方案 1: 调用本地 Python 后端
        const localEndpoint = this.getEndpointUrl('chat');

        try {
            const response = await fetch(localEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage,
                    context: this.messages.slice(-10), // 最近 10 条消息
                }),
            });

            if (response.ok) {
                const data = await response.json();
                const aiMsg: ChatMessage = {
                    role: 'assistant',
                    content: data.content,
                    timestamp: new Date().toISOString(),
                };
                this.messages.push(aiMsg);
                return aiMsg;
            }
        } catch (error) {
            console.warn('本地后端不可用，使用模拟回复');
        }

        // 方案 2: 模拟回复 (开发 fallback)
        const aiMsg: ChatMessage = {
            role: 'assistant',
            content: this.generateFallbackResponse(userMessage),
            timestamp: new Date().toISOString(),
        };
        this.messages.push(aiMsg);
        return aiMsg;
    }

    // 生成占位回复
    private generateFallbackResponse(input: string): string {
        const responses = [
            '嗯嗯，我明白了！',
            '这个话题很有趣呢～',
            '让我想想... 🤔',
            '你说得对！',
            '好哒，交给我吧！',
        ];
        return responses[Math.floor(Math.random() * responses.length)];
    }

    private getEndpointUrl(kind: 'chat' | 'history' | 'memory' | 'companions' | 'companions-active' | 'models-imported'): string {
        const endpoint = new URL(this.config.apiEndpoint || 'http://localhost:8080/chat');
        const pathSegments = endpoint.pathname.split('/').filter(Boolean);

        const targetPath = {
            chat: 'chat',
            history: 'history',
            memory: 'memory',
            companions: 'companions',
            'companions-active': 'companions/active',
            'models-imported': 'models/imported',
        }[kind];

        if (pathSegments.length === 0) {
            endpoint.pathname = `/${targetPath}`;
            return endpoint.toString();
        }

        pathSegments[pathSegments.length - 1] = targetPath;
        endpoint.pathname = `/${pathSegments.join('/')}`;
        return endpoint.toString();
    }

    private async buildApiRequestError(message: string, response: Response): Promise<ApiRequestError> {
        let detail: string | null = null;

        try {
            const data = await response.json() as { detail?: unknown };
            if (typeof data.detail === 'string') {
                detail = data.detail;
            }
        } catch {
            detail = null;
        }

        return new ApiRequestError(`${message}: ${response.status}`, response.status, detail);
    }

    // 获取历史消息
    public getHistory(limit: number = 20): ChatMessage[] {
        return this.messages.slice(-limit);
    }

    // 清空消息
    public clear() {
        this.messages = [];
    }

    // 通知监听器
    private notify(msg: ChatMessage) {
        this.listeners.forEach((cb) => cb(msg));
    }
}
