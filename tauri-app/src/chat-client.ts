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
    memoryContextProvider?: () => ChatMessage[];
    historyContextProvider?: () => ChatMessage[];
}

export interface MemoryItem {
    id: number;
    content: string;
    category: string;
    importance: number;
    scope?: string;
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

export interface CatalogModelItem {
    key: string;
    name: string;
    preview_path: string;
    builtin: boolean;
    installed: boolean;
}

export interface DataDirInfo {
    data_dir: string;
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

    private buildRequestContext(): ChatMessage[] {
        const memoryContext = this.config.memoryContextProvider?.() ?? [];
        const historyContext = this.config.historyContextProvider?.() ?? [];
        return [...memoryContext, ...historyContext, ...this.messages.slice(-10)];
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

    public async streamAndYield(
        content: string,
        onDelta: (chunk: string) => void,
        onState?: (state: string) => void,
    ): Promise<string> {
        const userMsg: ChatMessage = {
            role: 'user',
            content,
            timestamp: new Date().toISOString(),
        };
        this.messages.push(userMsg);

        const response = await fetch(this.getEndpointUrl('chat-stream'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: content,
                context: this.buildRequestContext(),
            }),
        }).catch(() => null);

        if (!response || !response.ok || !response.body) {
            return this.fallbackFromStreaming(content, onDelta, onState);
        }

        try {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let currentEvent = '';
            let finalContent = '';

            const processBlock = (block: string) => {
                const lines = block.split('\n');
                let data = '';

                for (const rawLine of lines) {
                    const line = rawLine.trimEnd();
                    if (line.startsWith('event:')) {
                        currentEvent = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        data += line.slice(5).trimStart();
                    }
                }

                if ((currentEvent === 'state' || currentEvent === 'phase') && onState) {
                    onState(data);
                }
                if (currentEvent === 'assistant_delta') {
                    finalContent += data;
                    onDelta(data);
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

                const blocks = buffer.split('\n\n');
                buffer = blocks.pop() || '';

                for (const block of blocks) {
                    processBlock(block);
                }

                if (done) {
                    break;
                }
            }

            if (buffer.trim()) {
                processBlock(buffer);
            }

            if (!finalContent.trim()) {
                throw new Error('Streaming response completed without assistant content');
            }

            const aiMsg: ChatMessage = {
                role: 'assistant',
                content: finalContent,
                timestamp: new Date().toISOString(),
            };
            this.messages.push(aiMsg);
            return finalContent;
        } catch (error) {
            console.warn('Streaming chat failed, falling back to standard chat.', error);
            return this.fallbackFromStreaming(content, onDelta, onState);
        }
    }

    private async fallbackFromStreaming(
        content: string,
        onDelta: (chunk: string) => void,
        onState?: (state: string) => void,
    ): Promise<string> {
        onState?.('thinking');
        const fallbackMessage = await this.callAI(content);
        onDelta(fallbackMessage.content);
        return fallbackMessage.content;
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

    public async loadCatalogModels(): Promise<CatalogModelItem[]> {
        const response = await fetch(this.getEndpointUrl('models-catalog'));
        if (!response.ok) {
            throw new Error(`Catalog models request failed: ${response.status}`);
        }
        return await response.json() as CatalogModelItem[];
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

    public async installCatalogModel(modelKey: string): Promise<void> {
        const response = await fetch(this.getEndpointUrl('models-catalog-install'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_key: modelKey }),
        });
        if (!response.ok) {
            throw await this.buildApiRequestError('Install catalog model failed', response);
        }
    }

    public async loadDataDir(): Promise<DataDirInfo> {
        const response = await fetch(this.getEndpointUrl('data-dir'));
        if (!response.ok) {
            throw new Error(`Data dir request failed: ${response.status}`);
        }
        return await response.json() as DataDirInfo;
    }

    public async saveDataDir(dataDir: string): Promise<DataDirInfo> {
        const response = await fetch(this.getEndpointUrl('data-dir'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_dir: dataDir, migrate_existing: true }),
        });
        if (!response.ok) {
            throw await this.buildApiRequestError('Save data dir failed', response);
        }
        return await response.json() as DataDirInfo;
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
                    context: this.buildRequestContext(),
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

    private getEndpointUrl(kind: 'chat' | 'chat-stream' | 'history' | 'memory' | 'companions' | 'companions-active' | 'models-imported' | 'models-catalog' | 'models-catalog-install' | 'data-dir'): string {
        const endpoint = new URL(this.config.apiEndpoint || 'http://119.91.32.174:8080/chat');
        const pathSegments = endpoint.pathname.split('/').filter(Boolean);

        const targetPath = {
            chat: 'chat',
            'chat-stream': 'chat/stream',
            history: 'history',
            memory: 'memory',
            companions: 'companions',
            'companions-active': 'companions/active',
            'models-imported': 'models/imported',
            'models-catalog': 'models/catalog',
            'models-catalog-install': 'models/catalog/install',
            'data-dir': 'data-dir',
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
