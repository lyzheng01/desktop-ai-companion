/**
 * Desktop AI Companion - 主入口
 * Live2D 角色渲染 + 聊天交互
 */

import * as PIXI from 'pixi.js';
import { invoke } from '@tauri-apps/api/core';
import { LogicalSize, PhysicalPosition } from '@tauri-apps/api/dpi';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { ApiRequestError, ChatClient, type ChatMessage, type CompanionProfile, type ImportedModelItem, type MemoryItem } from './chat-client';
import { HIYORI_ACTIONS, HIYORI_ACTION_KEYS, type HiyoriAction } from './hiyori-actions';

// ============== 全局状态 ==============

type AppSettings = {
    user_nickname: string;
    user_display_name: string;
    character_type: string;
    character_name: string;
    personality: string[];
    interaction_mode: string;
    proactive_mode: string;
    chat_model: string;
    window_x: number;
    window_y: number;
    window_scale: number;
    character_scales: Record<string, number>;
};

type CharacterBehavior = {
    idleGroups: string[];
    tapGroups: string[];
    greetGroups: string[];
    talkGroups: string[];
    supportsRandomExpression: boolean;
};

type CharacterRegion = 'face' | 'chest' | 'arms' | 'belly' | 'legs';
type HiyoriActionHandler = () => void;
type CompanionState = 'idle' | 'listening' | 'thinking' | 'talking';

let app: PIXI.Application;
let currentModel: any = null;
let chatWindowVisible = false;
let pointerDown = false;
let dragStarted = false;
let pointerStartX = 0;
let pointerStartY = 0;
let pointerLocalX = 0;
let pointerLocalY = 0;
let windowStartX = 0;
let windowStartY = 0;
let characterHidden = false;
let chatHistoryLoaded = false;
let chatHistoryLoadPromise: Promise<void> | null = null;
let currentScale = 1;
let autoFitScale = 1;
let baseModelX = 0;
let baseModelY = 0;
let idleActionTimer: number | null = null;
let talkLoopTimer: number | null = null;
let talkStopTimer: number | null = null;
let talkingSessionId = 0;
let customAnimationTimer: number | null = null;
let stageAnimationFrame: number | null = null;
let actionIndicatorTimer: number | null = null;
let bubbleTimer: number | null = null;
let lastBubbleLine = '';
let firstRunRequired = false;
let desktopFlowStarted = false;
let bootstrapActiveCompanion: CompanionProfile | null = null;
let pendingFirstRunCompanionId: number | null = null;
let cachedCompanions: CompanionProfile[] = [];
const FREE_COMPANION_LIMIT = 1;
const BASE_WINDOW_WIDTH = 400;
const BASE_WINDOW_HEIGHT = 600;
const chatClient = new ChatClient({
    apiEndpoint: 'http://localhost:8080/chat',
});
const cubismCoreUrl = '/vendor/live2dcubismcore.min.js';
const live2dModels: Record<string, string> = {
    kei: '/live2d/kei_en/kei_basic_free/runtime/kei_basic_free.model3.json',
    chitose: '/live2d/chitose/chitose_t02.model3.json',
    hiyori: '/live2d/hiyori/hiyori_pro_jp.model3.json',
    shizuku: '/live2d/shizuku/runtime/shizuku.model3.json',
    hiyori_pro_zh: '/live2d/hiyori_pro_zh/runtime/hiyori_pro_t11.model3.json',
    mao_pro_zh: '/live2d/mao_pro_zh/runtime/mao_pro.model3.json',
    miara_pro_en: '/live2d/miara_pro_en/runtime/miara_pro_t03.model3.json',
    miku_pro_jp: '/live2d/miku_pro_jp/runtime/miku_sample_t04.model3.json',
    natori_pro_zh: '/live2d/natori_pro_zh/runtime/natori_pro_t06.model3.json',
    ren_pro_zh: '/live2d/ren_pro_zh/runtime/ren.model3.json',
};
const modelDisplayNames: Record<string, string> = {
    kei: 'Kei',
    chitose: 'Chitose',
    hiyori: 'Hiyori JP',
    shizuku: 'Shizuku',
    hiyori_pro_zh: 'Hiyori',
    mao_pro_zh: 'Mao',
    miara_pro_en: 'Miara',
    miku_pro_jp: 'Miku',
    natori_pro_zh: 'Natori',
    ren_pro_zh: 'Ren',
};
const importedModelKeys = new Set<string>();
let currentCharacter = 'hiyori_pro_zh';
const characterBehaviors: Record<string, CharacterBehavior> = {
    kei: {
        idleGroups: [''],
        tapGroups: [''],
        greetGroups: [''],
        talkGroups: [''],
        supportsRandomExpression: false,
    },
    chitose: {
        idleGroups: ['Idle'],
        tapGroups: ['Tap'],
        greetGroups: ['Flick'],
        talkGroups: ['Idle', 'Tap'],
        supportsRandomExpression: true,
    },
    hiyori: {
        idleGroups: ['Idle'],
        tapGroups: ['Tap', 'Tap@Body'],
        greetGroups: ['Flick', 'Flick@Body'],
        talkGroups: ['Idle', 'FlickUp', 'FlickDown'],
        supportsRandomExpression: false,
    },
};
const bubbleLines = {
    gentle: [
        '我在呢。',
        '怎么啦？',
        '嗯，我听到了。',
        '有事找我吗？',
        '我在旁边陪着你。',
    ],
    cheerful: [
        '嘿嘿，你点到我啦。',
        '我有在认真看你哦。',
        '今天也想陪你一下。',
        '诶嘿，我在这儿。',
        '要不要和我说一句话？',
    ],
    shy: [
        '欸？',
        '突然点我呀。',
        '唔，被发现了。',
        '嗯？怎么啦？',
        '我还以为你在忙呢。',
    ],
    calm: [
        '我会在这儿待着的。',
        '慢慢来也没关系。',
        '如果你想说话，我在。',
        '先陪你一下。',
        '我没有走开哦。',
    ],
} as const;
let appSettings: AppSettings = {
    user_nickname: '小伙伴',
    user_display_name: '你',
    character_type: 'hiyori_pro_zh',
    character_name: '小艾',
    personality: ['温柔'],
    interaction_mode: 'work',
    proactive_mode: 'quiet',
    chat_model: 'gpt',
    window_x: 100,
    window_y: 100,
    window_scale: 1,
    character_scales: {},
};
const live2dDebugState = {
    currentCharacter,
    idleActive: false,
    talkingActive: false,
    hiyoriActions: null as Record<HiyoriAction, string> | null,
};

function logProductEvent(name: string, payload: Record<string, unknown> = {}) {
    console.log(`PRODUCT_EVENT ${name} ${JSON.stringify(payload)}`);
}

function setCompanionState(state: CompanionState) {
    document.body.dataset.companionState = state;
    console.log(`COMPANION_STATE: ${state}`);
}

async function loadAppSettings(options: {
    preserveBootstrapCompanion?: boolean;
    activeCompanionOverride?: CompanionProfile | null;
} = {}) {
    try {
        const response = await fetch('http://localhost:8080/config');
        if (!response.ok) {
            throw new Error(`Config request failed: ${response.status}`);
        }

        const data = await response.json() as AppSettings;
        appSettings = {
            user_nickname: data.user_nickname ?? '小伙伴',
            user_display_name: data.user_display_name ?? '你',
            character_type: data.character_type ?? 'kei',
            character_name: data.character_name ?? '小艾',
            personality: data.personality ?? ['温柔'],
            interaction_mode: data.interaction_mode ?? 'work',
            proactive_mode: data.proactive_mode ?? 'quiet',
            chat_model: data.chat_model ?? 'gpt',
            window_x: data.window_x ?? 100,
            window_y: data.window_y ?? 100,
            window_scale: data.window_scale ?? 1,
            character_scales: data.character_scales ?? {},
        };

        if (options.activeCompanionOverride) {
            applyActiveCompanion(options.activeCompanionOverride);
        } else if (options.preserveBootstrapCompanion && bootstrapActiveCompanion) {
            applyActiveCompanion(bootstrapActiveCompanion);
        }

        currentCharacter = live2dModels[appSettings.character_type] ? appSettings.character_type : 'kei';
    } catch (error) {
        console.warn('Failed to load config, using defaults.', error);
    }
}

async function saveAppSettings() {
    appSettings.character_type = currentCharacter;
    appSettings.window_scale = currentScale;

    try {
        await fetch('http://localhost:8080/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(appSettings),
        });
    } catch (error) {
        console.warn('Failed to save config.', error);
    }
}

function updateChatTitle() {
    const title = document.getElementById('chat-title');
    if (title) {
        title.textContent = `${appSettings.character_name} AI`;
    }
}

function getCharacterDisplayName(name: string) {
    return modelDisplayNames[name] ?? name;
}

function getImportedModelKey(model: ImportedModelItem) {
    return `imported:${model.id}`;
}

function getGeneratedPreviewPath(modelKey: string) {
    if (modelKey.startsWith('imported:')) {
        const importedId = modelKey.split(':')[1] || 'unknown';
        return `/model-previews/imported/${importedId}.png`;
    }
    return `/model-previews/builtin/${modelKey}.png`;
}

function getModelPreviewCandidates(modelPath: string) {
    const normalized = modelPath.replace(/\\/g, '/');
    const slashIndex = normalized.lastIndexOf('/');
    const dir = slashIndex >= 0 ? normalized.slice(0, slashIndex) : normalized;
    const file = slashIndex >= 0 ? normalized.slice(slashIndex + 1) : normalized;
    const stem = file.replace(/\.model3\.json$/i, '');

    const candidates = [
        `${dir}/icon.png`,
        `${dir}/icon.jpg`,
        `${dir}/preview.png`,
        `${dir}/preview.jpg`,
        `${dir}/${stem}.png`,
        `${dir}/${stem}.jpg`,
        `${dir}/${stem}.1024/texture_00.png`,
        `${dir}/${stem}.2048/texture_00.png`,
        `${dir}/${stem}.4096/texture_00.png`,
        `${dir}/texture_00.png`,
    ];

    return candidates.filter((candidate, index) => candidates.indexOf(candidate) === index);
}

function buildModelCard(name: string, detailText: string, modelKey: string, modelPath: string) {
    const card = document.createElement('div');
    card.className = 'model-card';

    const thumb = document.createElement('div');
    thumb.className = 'model-thumb';

    const img = document.createElement('img');
    const previewCandidates = [
        getGeneratedPreviewPath(modelKey),
        ...getModelPreviewCandidates(modelPath),
    ];
    let previewIndex = 0;
    const tryNextPreview = () => {
        const next = previewCandidates[previewIndex++];
        if (!next) return;
        img.src = next;
    };
    img.alt = name;
    img.addEventListener('error', tryNextPreview);
    tryNextPreview();
    thumb.appendChild(img);

    const meta = document.createElement('div');
    meta.className = 'model-meta';

    const title = document.createElement('span');
    title.className = 'model-name';
    title.textContent = name;

    const detail = document.createElement('span');
    detail.className = 'model-detail';
    detail.textContent = detailText;

    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = modelKey === currentCharacter ? '当前使用中' : '切换';
    button.disabled = modelKey === currentCharacter;
    button.addEventListener('click', () => {
        closeModelPanel();
        switchCharacter(modelKey);
        void refreshModelPanel();
    });

    meta.appendChild(title);
    meta.appendChild(detail);
    card.dataset.modelKey = modelKey;
    card.appendChild(thumb);
    card.appendChild(meta);
    card.appendChild(button);
    return card;
}

function syncImportedModelRegistry(models: ImportedModelItem[]) {
    importedModelKeys.forEach((key) => {
        delete live2dModels[key];
        delete modelDisplayNames[key];
    });
    importedModelKeys.clear();

    models.forEach((model) => {
        const key = getImportedModelKey(model);
        importedModelKeys.add(key);
        live2dModels[key] = model.model_path;
        modelDisplayNames[key] = model.name;
    });
}

function getInteractionModeLabel(mode: string) {
    const labels: Record<string, string> = {
        work: '工作搭子',
        daily: '日常陪伴',
        quiet: '少打扰助手',
        sleep: '睡前聊天伙伴',
    };
    return labels[mode] ?? mode;
}

function getCurrentBehavior() {
    return characterBehaviors[currentCharacter] ?? characterBehaviors.kei;
}

function isHiyoriCharacter() {
    return currentCharacter === 'hiyori' || currentCharacter === 'hiyori_pro_zh';
}

function getRandomItem<T>(items: T[]): T | null {
    if (items.length === 0) return null;
    return items[Math.floor(Math.random() * items.length)] ?? null;
}

function updateCharacterLabel() {
    const label = document.getElementById('current-character-label');
    if (label) {
        label.textContent = getCharacterDisplayName(currentCharacter);
    }
    updateChatTitle();
}

function normalizeFirstRunPersonalityTags(tags: string[]) {
    const uniqueTags = Array.from(new Set(tags));
    const limitedTags = uniqueTags.slice(0, 3);
    return limitedTags.length > 0 ? limitedTags : ['温柔'];
}

function syncFirstRunPersonalitySelection() {
    const personalitySelect = document.getElementById('creator-personality-select') as HTMLSelectElement | null;
    if (!personalitySelect) {
        return ['温柔'];
    }

    const selectedTags = normalizeFirstRunPersonalityTags(
        Array.from(personalitySelect.selectedOptions).map((option) => option.value),
    );
    Array.from(personalitySelect.options).forEach((option) => {
        option.selected = selectedTags.includes(option.value);
    });
    return selectedTags;
}

function applyActiveCompanion(active: CompanionProfile) {
    appSettings.character_name = active.name;
    appSettings.character_type = active.character_type;
    appSettings.personality = active.personality_tags.length > 0 ? active.personality_tags : ['温柔'];
    appSettings.interaction_mode = active.interaction_mode;
    currentCharacter = live2dModels[active.character_type] ? active.character_type : 'kei';
}

function isSingleCompanionBootstrapCandidate(companions: CompanionProfile[]) {
    return companions.length === 1;
}

function getCreateCompanionErrorMessage(error: unknown) {
    if (error instanceof ApiRequestError && error.status === 403) {
        return '普通用户最多创建 1 个伙伴，请直接使用现有伙伴。';
    }

    return '创建伙伴失败，请稍后重试。';
}

async function determineCompanionBootstrapState() {
    const active = await chatClient.loadActiveCompanion();
    if (active) {
        firstRunRequired = false;
        bootstrapActiveCompanion = active;
        pendingFirstRunCompanionId = active.id;
        applyActiveCompanion(active);
        return;
    }

    const companions = await chatClient.loadCompanions();
    if (isSingleCompanionBootstrapCandidate(companions)) {
        const existingCompanion = companions[0];
        await chatClient.activateCompanion(existingCompanion.id);
        firstRunRequired = false;
        bootstrapActiveCompanion = { ...existingCompanion, is_active: true };
        pendingFirstRunCompanionId = existingCompanion.id;
        applyActiveCompanion(bootstrapActiveCompanion);
        return;
    }

    firstRunRequired = companions.length === 0;
    bootstrapActiveCompanion = null;
    pendingFirstRunCompanionId = null;
}

function showBootstrapError(message: string) {
    const banner = document.getElementById('bootstrap-error-banner');
    if (banner) {
        banner.textContent = message;
        banner.classList.add('visible');
    }
}

function hideBootstrapError() {
    const banner = document.getElementById('bootstrap-error-banner');
    if (banner) {
        banner.textContent = '';
        banner.classList.remove('visible');
    }
}

function showFirstRunPanel() {
    const panel = document.getElementById('first-run-panel');
    panel?.classList.add('visible');
}

function hideFirstRunPanel() {
    const panel = document.getElementById('first-run-panel');
    panel?.classList.remove('visible');
}

function bindFirstRunCreator() {
    const personalitySelect = document.getElementById('creator-personality-select') as HTMLSelectElement | null;
    personalitySelect?.addEventListener('change', () => {
        syncFirstRunPersonalitySelection();
    });

    const submitButton = document.getElementById('creator-submit-btn');
    submitButton?.addEventListener('click', async () => {
        const nameInput = document.getElementById('creator-name-input') as HTMLInputElement | null;
        const characterSelect = document.getElementById('creator-character-select') as HTMLSelectElement | null;
        const modeSelect = document.getElementById('creator-mode-select') as HTMLSelectElement | null;

        const name = nameInput?.value.trim() || '小艾';
        const characterType = characterSelect?.value || 'hiyori_pro_zh';
        const personalityTags = syncFirstRunPersonalitySelection();
        const interactionMode = modeSelect?.value || 'work';

        submitButton.setAttribute('disabled', 'true');

        try {
            hideBootstrapError();
            let companionId = pendingFirstRunCompanionId;
            if (companionId === null) {
                companionId = await chatClient.createCompanion({
                    name,
                    character_type: characterType,
                    personality_tags: personalityTags,
                    interaction_mode: interactionMode,
                });
                pendingFirstRunCompanionId = companionId;
            }

            await chatClient.activateCompanion(companionId);
            pendingFirstRunCompanionId = null;
            bootstrapActiveCompanion = {
                id: companionId,
                name,
                character_type: characterType,
                personality_tags: personalityTags,
                interaction_mode: interactionMode,
                is_active: true,
            };
            applyActiveCompanion(bootstrapActiveCompanion);
            firstRunRequired = false;
            hideFirstRunPanel();
            await enterDesktopFlow();
        } catch (error) {
            console.error('Failed to create first companion.', error);
            firstRunRequired = true;
            showFirstRunPanel();
            showBootstrapError(getCreateCompanionErrorMessage(error));
        } finally {
            submitButton.removeAttribute('disabled');
        }
    });
}

function syncCompanionSettingsForm() {
    const nameInput = document.getElementById('character-name-input') as HTMLInputElement | null;
    if (nameInput) {
        nameInput.value = appSettings.character_name;
    }

    const personalitySelect = document.getElementById('personality-select') as HTMLSelectElement | null;
    if (personalitySelect) {
        Array.from(personalitySelect.options).forEach((option) => {
            option.selected = appSettings.personality.includes(option.value);
        });
    }

    const interactionModeSelect = document.getElementById('interaction-mode-select') as HTMLSelectElement | null;
    if (interactionModeSelect) {
        interactionModeSelect.value = appSettings.interaction_mode;
    }

    const proactiveModeSelect = document.getElementById('proactive-mode-select') as HTMLSelectElement | null;
    if (proactiveModeSelect) {
        proactiveModeSelect.value = appSettings.proactive_mode;
    }

    const userDisplayNameInput = document.getElementById('user-display-name-input') as HTMLInputElement | null;
    if (userDisplayNameInput) {
        userDisplayNameInput.value = appSettings.user_display_name;
    }

    const chatModelSelect = document.getElementById('chat-model-select') as HTMLSelectElement | null;
    if (chatModelSelect) {
        chatModelSelect.value = appSettings.chat_model;
    }

    const companionLimitNote = document.getElementById('companion-limit-note');
    if (companionLimitNote) {
        companionLimitNote.textContent = `普通用户最多创建 ${FREE_COMPANION_LIMIT} 个伙伴，更多伙伴为 VIP 功能。`;
    }

    const activeCompanionSummary = document.getElementById('active-companion-summary');
    if (activeCompanionSummary) {
        activeCompanionSummary.textContent = `当前伙伴：${appSettings.character_name} · ${getCharacterDisplayName(currentCharacter)} · ${getInteractionModeLabel(appSettings.interaction_mode)}`;
    }
}

function renderCompanionList(companions: CompanionProfile[]) {
    const list = document.getElementById('companion-list');
    if (!list) {
        return;
    }

    cachedCompanions = companions;
    list.innerHTML = '';

    const activeCompanion = companions.find((companion) => companion.is_active);
    const activeCompanionSummary = document.getElementById('active-companion-summary');
    if (activeCompanionSummary) {
        if (activeCompanion) {
            activeCompanionSummary.textContent = `当前伙伴：${activeCompanion.name} · ${getCharacterDisplayName(activeCompanion.character_type)} · ${getInteractionModeLabel(activeCompanion.interaction_mode)}`;
        } else {
            activeCompanionSummary.textContent = '当前伙伴：未选择';
        }
    }

    companions.forEach((companion) => {
        const row = document.createElement('div');
        row.className = 'companion-list-item';

        const meta = document.createElement('div');
        meta.className = 'companion-list-meta';

        const name = document.createElement('span');
        name.className = 'companion-list-name';
        name.textContent = companion.name;

        const detail = document.createElement('span');
        detail.className = 'companion-list-detail';
        detail.textContent = `${getCharacterDisplayName(companion.character_type)} · ${getInteractionModeLabel(companion.interaction_mode)}`;

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'companion-switch-btn';
        button.dataset.companionSwitchId = String(companion.id);
        button.textContent = companion.is_active ? '当前使用中' : '切换';
        button.disabled = companion.is_active;
        button.addEventListener('click', () => {
            void switchActiveCompanion(companion.id);
        });

        meta.appendChild(name);
        meta.appendChild(detail);
        row.appendChild(meta);
        row.appendChild(button);
        list.appendChild(row);
    });

    const createCompanionButton = document.getElementById('create-companion-btn') as HTMLButtonElement | null;
    if (createCompanionButton) {
        const canCreateCompanion = companions.length < FREE_COMPANION_LIMIT;
        createCompanionButton.disabled = !canCreateCompanion;
        createCompanionButton.textContent = canCreateCompanion ? '创建新伙伴' : '创建新伙伴（VIP）';
    }
}

async function refreshCompanionList(activeCompanionId: number | null = null) {
    try {
        const companions = await chatClient.loadCompanions();
        const nextCompanions = activeCompanionId === null
            ? companions
            : companions.map((companion) => ({
                ...companion,
                is_active: companion.id === activeCompanionId,
            }));
        renderCompanionList(nextCompanions);
    } catch (error) {
        console.warn('Failed to load companion list.', error);
    }
}

function getConfirmedActiveCompanionOrThrow(activeCompanion: CompanionProfile | null, requestedCompanionId: number) {
    if (!activeCompanion) {
        throw new Error('Active companion confirmation returned null.');
    }

    if (activeCompanion.id !== requestedCompanionId) {
        throw new Error(`Active companion confirmation mismatch: expected ${requestedCompanionId}, got ${activeCompanion.id}.`);
    }

    return activeCompanion;
}

async function switchActiveCompanion(companionId: number) {
    const list = document.getElementById('companion-list');
    const previousCompanions = cachedCompanions.map((companion) => ({ ...companion }));
    list?.querySelectorAll<HTMLButtonElement>('.companion-switch-btn').forEach((button) => {
        button.disabled = true;
    });

    try {
        hideBootstrapError();
        await chatClient.activateCompanion(companionId);
        const activeCompanion = getConfirmedActiveCompanionOrThrow(
            await chatClient.loadActiveCompanion(),
            companionId,
        );
        bootstrapActiveCompanion = activeCompanion;
        pendingFirstRunCompanionId = null;

        await loadAppSettings({ activeCompanionOverride: activeCompanion });
        updateCharacterLabel();
        syncCompanionSettingsForm();

        if (desktopFlowStarted) {
            await loadLive2DModel();
        }

        const nextCompanions = (cachedCompanions.length > 0 ? cachedCompanions : await chatClient.loadCompanions()).map((companion) => ({
            ...companion,
            is_active: companion.id === activeCompanion.id,
        }));
        renderCompanionList(nextCompanions);
    } catch (error) {
        console.error('Failed to switch active companion.', error);
        showBootstrapError('切换伙伴失败，请稍后重试。');
        if (previousCompanions.length > 0) {
            renderCompanionList(previousCompanions);
        } else {
            await refreshCompanionList();
        }
    }
}

function bindCompanionSettingsForm() {
    const nameInput = document.getElementById('character-name-input') as HTMLInputElement | null;
    nameInput?.addEventListener('change', () => {
        appSettings.character_name = nameInput.value.trim() || '小艾';
        syncCompanionSettingsForm();
        updateChatTitle();
        void saveAppSettings();
    });

    const userDisplayNameInput = document.getElementById('user-display-name-input') as HTMLInputElement | null;
    userDisplayNameInput?.addEventListener('change', () => {
        appSettings.user_display_name = userDisplayNameInput.value.trim() || '你';
        syncCompanionSettingsForm();
        void saveAppSettings();
    });

    const personalitySelect = document.getElementById('personality-select') as HTMLSelectElement | null;
    personalitySelect?.addEventListener('change', () => {
        const selected = Array.from(personalitySelect.selectedOptions).map((item) => item.value);
        appSettings.personality = selected.length > 0 ? selected : ['温柔'];
        syncCompanionSettingsForm();
        void saveAppSettings();
    });

    const chatModelSelect = document.getElementById('chat-model-select') as HTMLSelectElement | null;
    chatModelSelect?.addEventListener('change', () => {
        appSettings.chat_model = chatModelSelect.value;
        void saveAppSettings();
    });

    const interactionModeSelect = document.getElementById('interaction-mode-select') as HTMLSelectElement | null;
    interactionModeSelect?.addEventListener('change', () => {
        appSettings.interaction_mode = interactionModeSelect.value;
        void saveAppSettings();
    });

    const proactiveModeSelect = document.getElementById('proactive-mode-select') as HTMLSelectElement | null;
    proactiveModeSelect?.addEventListener('change', () => {
        appSettings.proactive_mode = proactiveModeSelect.value;
        void saveAppSettings();
    });

    const createCompanionButton = document.getElementById('create-companion-btn') as HTMLButtonElement | null;
    createCompanionButton?.addEventListener('click', () => {
        if (createCompanionButton.disabled) {
            return;
        }

        pendingFirstRunCompanionId = null;
        hideBootstrapError();
        showFirstRunPanel();
    });
}

function updateScaleControls() {
    const slider = document.getElementById('scale-slider') as HTMLInputElement | null;
    const value = document.getElementById('scale-value');
    if (slider) {
        slider.value = currentScale.toFixed(2);
    }
    if (value) {
        value.textContent = `${Math.round(currentScale * 100)}%`;
    }
}

function updateHideMenuLabel() {
    const hideButton = document.querySelector<HTMLElement>('[data-action="hide"]');
    if (hideButton) {
        hideButton.textContent = characterHidden ? '👁 显示' : '🙈 隐藏';
    }
}

function hideReactionBubble() {
    const bubble = document.getElementById('reaction-bubble');
    if (bubble) {
        bubble.classList.remove('visible');
    }
    if (bubbleTimer !== null) {
        window.clearTimeout(bubbleTimer);
        bubbleTimer = null;
    }
}

function showReactionBubble(text: string) {
    const bubble = document.getElementById('reaction-bubble');
    const textNode = document.getElementById('reaction-bubble-text');
    if (!bubble || !textNode) return;

    textNode.textContent = text;
    bubble.classList.add('visible');
    if (bubbleTimer !== null) {
        window.clearTimeout(bubbleTimer);
    }
    bubbleTimer = window.setTimeout(() => {
        bubble.classList.remove('visible');
        bubbleTimer = null;
    }, 1800);
}

function pickNonRepeatingLine(lines: readonly string[]) {
    const filtered = lines.filter((line) => line !== lastBubbleLine);
    const pool = filtered.length > 0 ? filtered : lines;
    const next = pool[Math.floor(Math.random() * pool.length)] ?? lines[0];
    lastBubbleLine = next;
    return next;
}

function getBubbleLineForRegion(region: CharacterRegion) {
    switch (region) {
        case 'face':
            return pickNonRepeatingLine(bubbleLines.gentle);
        case 'arms':
            return pickNonRepeatingLine(bubbleLines.cheerful);
        case 'chest':
        case 'belly':
            return pickNonRepeatingLine(bubbleLines.shy);
        case 'legs':
        default:
            return pickNonRepeatingLine(bubbleLines.calm);
    }
}

async function handleCompanionSingleClick(region: CharacterRegion) {
    await triggerRegionReaction(region);
    await new Promise((resolve) => window.setTimeout(resolve, 160));
    showReactionBubble(getBubbleLineForRegion(region));
}

function getScaledWindowSize(scale: number) {
    return {
        width: Math.round(BASE_WINDOW_WIDTH * scale),
        height: Math.round(BASE_WINDOW_HEIGHT * scale),
    };
}

function applyScaledViewport() {
    const container = document.getElementById('character-container');
    if (container) {
        const { width, height } = getScaledWindowSize(currentScale);
        container.style.width = `${width}px`;
        container.style.height = `${height}px`;
    }

    if (app) {
        const { width, height } = getScaledWindowSize(currentScale);
        app.renderer.resize(width, height);
    }
}

function computeFitScale() {
    if (!currentModel) return 1;

    currentModel.scale.set(1, 1);
    const fitScale = Math.min(
        (app.screen.width * 0.9) / currentModel.width,
        (app.screen.height * 0.92) / currentModel.height,
    );

    return Number.isFinite(fitScale) && fitScale > 0 ? fitScale : 1;
}

function applyCurrentScale() {
    if (!currentModel) return;
    applyScaledViewport();
    const fitScale = computeFitScale();
    autoFitScale = fitScale;
    currentModel.scale.set(fitScale, fitScale);
    baseModelX = (app.screen.width - currentModel.width) / 2;
    baseModelY = app.screen.height - currentModel.height;
    currentModel.x = baseModelX;
    currentModel.y = baseModelY;
    currentModel.rotation = 0;
    currentModel.skew.set(0, 0);
    updateScaleControls();
}

async function setScale(scale: number, persist = true) {
    currentScale = Math.min(1.4, Math.max(0.01, scale));
    appSettings.character_scales[currentCharacter] = currentScale;
    applyCurrentScale();

    const { width, height } = getScaledWindowSize(currentScale);
    try {
        await getCurrentWindow().setSize(new LogicalSize(width, height));
    } catch (error) {
        console.debug('Window resize failed.', error);
    }

    if (persist) {
        void saveAppSettings();
    }
}

function clearActionTimers() {
    if (idleActionTimer !== null) {
        window.clearTimeout(idleActionTimer);
        idleActionTimer = null;
    }
    if (talkLoopTimer !== null) {
        window.clearInterval(talkLoopTimer);
        talkLoopTimer = null;
    }
    if (talkStopTimer !== null) {
        window.clearTimeout(talkStopTimer);
        talkStopTimer = null;
    }
    if (customAnimationTimer !== null) {
        window.clearInterval(customAnimationTimer);
        customAnimationTimer = null;
    }
    if (stageAnimationFrame !== null) {
        window.cancelAnimationFrame(stageAnimationFrame);
        stageAnimationFrame = null;
    }
    live2dDebugState.idleActive = false;
    live2dDebugState.talkingActive = false;
}

function getLipSyncParameterIds(): string[] {
    const ids = currentModel?.internalModel?.settings?.getLipSyncParameters?.();
    if (Array.isArray(ids)) {
        return ids;
    }
    return [];
}

function setLipSyncValue(value: number) {
    const ids = getLipSyncParameterIds();
    ids.forEach((id) => {
        currentModel?.internalModel?.coreModel?.setParameterValueById?.(id, value, 1);
    });
}

function setModelParameter(id: string | undefined, value: number, weight = 1) {
    if (!id) return;
    currentModel?.internalModel?.coreModel?.setParameterValueById?.(id, value, weight);
}

function getCharacterStage() {
    return document.getElementById('character-stage');
}

function resetStageTransform() {
    const stage = getCharacterStage();
    if (stage) {
        stage.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
    }
}

function startCustomAnimation(
    durationMs: number,
    onFrame: (progress: number) => void,
    onFinish?: () => void,
) {
    if (customAnimationTimer !== null) {
        window.clearInterval(customAnimationTimer);
        customAnimationTimer = null;
    }

    const start = performance.now();
    customAnimationTimer = window.setInterval(() => {
        const elapsed = performance.now() - start;
        const progress = Math.min(1, elapsed / durationMs);
        onFrame(progress);

        if (progress >= 1) {
            if (customAnimationTimer !== null) {
                window.clearInterval(customAnimationTimer);
                customAnimationTimer = null;
            }
            onFinish?.();
        }
    }, 16);
}

function animateModelTransform(
    durationMs: number,
    onFrame: (progress: number) => void,
    onFinish?: () => void,
) {
    if (!currentModel) return;

    startCustomAnimation(durationMs, (progress) => {
        onFrame(progress);
    }, () => {
        applyCurrentScale();
        onFinish?.();
    });
}

function runHiyoriStageAction(
    durationMs: number,
    onFrame: (progress: number, stage: HTMLElement) => void,
    onFinish?: () => void,
) {
    const stage = getCharacterStage();
    if (!stage) return;

    if (stageAnimationFrame !== null) {
        window.cancelAnimationFrame(stageAnimationFrame);
        stageAnimationFrame = null;
    }

    const start = performance.now();
    const tick = (now: number) => {
        const progress = Math.min(1, (now - start) / durationMs);
        onFrame(progress, stage);

        if (progress >= 1) {
            stageAnimationFrame = null;
            resetStageTransform();
            onFinish?.();
            return;
        }

        stageAnimationFrame = window.requestAnimationFrame(tick);
    };

    stageAnimationFrame = window.requestAnimationFrame(tick);
}

function holdPose(progress: number, holdStart = 0.3, holdEnd = 0.72) {
    if (progress <= holdStart) {
        return progress / holdStart;
    }
    if (progress >= holdEnd) {
        return Math.max(0, 1 - (progress - holdEnd) / (1 - holdEnd));
    }
    return 1;
}

function playHiyoriAction(action: HiyoriAction) {
    if (!currentModel || currentCharacter !== 'hiyori') return;

    const model = currentModel.internalModel;
    const angleX = model?.idParamAngleX;
    const angleY = model?.idParamAngleY;
    const angleZ = model?.idParamAngleZ;
    const bodyX = model?.idParamBodyAngleX;

    if (customAnimationTimer !== null) {
        window.clearInterval(customAnimationTimer);
        customAnimationTimer = null;
    }
    if (stageAnimationFrame !== null) {
        window.cancelAnimationFrame(stageAnimationFrame);
        stageAnimationFrame = null;
    }

    resetStageTransform();
    applyCurrentScale();

    switch (action) {
        case 'nod':
            console.log('ACTION: hiyori-nod-full');
            animateNod();
            runHiyoriStageAction(760, (progress, stage) => {
                const wave = Math.sin(progress * Math.PI);
                stage.style.transform = `translate3d(0, ${10 * wave}px, 0) scale(${1 + 0.03 * wave}, ${1 - 0.05 * wave}) rotate(${-3 * wave}deg)`;
            });
            break;
        case 'shake':
            console.log('ACTION: hiyori-shake-full');
            animateShakeHead();
            runHiyoriStageAction(900, (progress, stage) => {
                const wave = Math.sin(progress * Math.PI * 3);
                stage.style.transform = `translate3d(${18 * wave}px, 0, 0) rotate(${6 * wave}deg) scale(${1 + 0.02 * Math.abs(wave)}, 1)`;
            });
            break;
        case 'chinRest':
            console.log('ACTION: hiyori-chinrest-full');
            animateChinRest();
            runHiyoriStageAction(1900, (progress, stage) => {
                const hold = holdPose(progress, 0.28, 0.78);
                stage.style.transform = `translate3d(${-42 * hold}px, ${18 * hold}px, 0) rotate(${-15 * hold}deg) scale(${1 + 0.03 * hold}, ${1 - 0.06 * hold})`;
                setModelParameter(angleX, -24 * hold);
                setModelParameter(angleY, 18 * hold);
                setModelParameter(angleZ, -24 * hold);
                setModelParameter(bodyX, -8 * hold);
            }, () => {
                setModelParameter(angleX, 0);
                setModelParameter(angleY, 0);
                setModelParameter(angleZ, 0);
                setModelParameter(bodyX, 0);
            });
            break;
        case 'wave':
            console.log('ACTION: hiyori-wave-full');
            void playMotionByCandidates(['Flick', 'Flick@Body']);
            runHiyoriStageAction(1200, (progress, stage) => {
                const wave = Math.sin(progress * Math.PI * 2);
                const rise = Math.sin(progress * Math.PI);
                stage.style.transform = `translate3d(${28 * wave}px, ${-18 * rise}px, 0) rotate(${12 * wave}deg) scale(${1 + 0.05 * rise}, ${1 - 0.02 * rise})`;
                setModelParameter(angleX, 8 * wave);
                setModelParameter(angleZ, 8 * wave);
            }, () => {
                setModelParameter(angleX, 0);
                setModelParameter(angleZ, 0);
            });
            break;
        case 'reject':
            console.log('ACTION: hiyori-reject-full');
            animateShakeHead();
            runHiyoriStageAction(980, (progress, stage) => {
                const wave = Math.sin(progress * Math.PI * 4);
                const rise = Math.sin(progress * Math.PI);
                stage.style.transform = `translate3d(${24 * wave}px, ${20 * rise}px, 0) rotate(${8 * wave}deg) scale(${1 + 0.04 * rise}, ${1 - 0.08 * rise})`;
                setModelParameter(bodyX, 10 * rise);
            }, () => {
                setModelParameter(bodyX, 0);
            });
            break;
        case 'crouch':
            console.log('ACTION: hiyori-crouch-full');
            runHiyoriStageAction(1600, (progress, stage) => {
                const dip = holdPose(progress, 0.25, 0.68);
                stage.style.transform = `translate3d(0, ${112 * dip}px, 0) scale(${1 + 0.16 * dip}, ${1 - 0.36 * dip}) rotate(${-6 * dip}deg)`;
                setModelParameter(bodyX, 14 * dip);
                setModelParameter(angleY, -10 * dip);
            }, () => {
                setModelParameter(bodyX, 0);
                setModelParameter(angleY, 0);
            });
            break;
    }
}

function animateNod() {
    const model = currentModel?.internalModel;
    if (!model) return;
    console.log('ACTION: nod');

    const angleY = model.idParamAngleY;
    const bodyX = model.idParamBodyAngleX;
    startCustomAnimation(760, (progress) => {
        const phase = Math.sin(progress * Math.PI);
        setModelParameter(angleY, -30 * phase);
        setModelParameter(bodyX, 12 * phase);
    }, () => {
        setModelParameter(angleY, 0);
        setModelParameter(bodyX, 0);
    });
}

function animateShakeHead() {
    const model = currentModel?.internalModel;
    if (!model) return;
    console.log('ACTION: shakeHead');

    const angleX = model.idParamAngleX;
    const angleZ = model.idParamAngleZ;
    startCustomAnimation(900, (progress) => {
        const wave = Math.sin(progress * Math.PI * 3);
        setModelParameter(angleX, 34 * wave);
        setModelParameter(angleZ, 14 * wave);
    }, () => {
        setModelParameter(angleX, 0);
        setModelParameter(angleZ, 0);
    });
}

function animateChinRest() {
    const model = currentModel?.internalModel;
    if (!model) return;
    console.log('ACTION: chinRest-params');

    const angleX = model.idParamAngleX;
    const angleY = model.idParamAngleY;
    const angleZ = model.idParamAngleZ;
    startCustomAnimation(1400, (progress) => {
        const rise = Math.sin(progress * Math.PI);
        setModelParameter(angleX, -18 * rise);
        setModelParameter(angleY, 10 * rise);
        setModelParameter(angleZ, -18 * rise);
    }, () => {
        setModelParameter(angleX, 0);
        setModelParameter(angleY, 0);
        setModelParameter(angleZ, 0);
    });
}

function animateCrouchLike() {
    if (!currentModel) return;
    console.log('ACTION: crouchLike-base');

    const baseY = app.screen.height - currentModel.height;
    startCustomAnimation(1000, (progress) => {
        const dip = Math.sin(progress * Math.PI);
        currentModel.y = baseY + 56 * dip;
        currentModel.scale.set(currentScale * (1 + 0.08 * dip), currentScale * (1 - 0.22 * dip));
    }, () => {
        applyCurrentScale();
    });
}

function animateBodyBounce(offsetX: number, offsetY: number, rotation: number, durationMs = 420) {
    if (!currentModel) return;

    animateModelTransform(durationMs, (progress) => {
        const wave = Math.sin(progress * Math.PI);
        currentModel.x = baseModelX + offsetX * wave;
        currentModel.y = baseModelY + offsetY * wave;
        currentModel.rotation = rotation * wave;
        currentModel.scale.set(currentScale * (1 + 0.04 * wave), currentScale * (1 - 0.04 * wave));
    });
}

function animateHeadTilt(rotation: number, offsetX: number, durationMs = 520) {
    if (!currentModel) return;

    animateModelTransform(durationMs, (progress) => {
        const wave = Math.sin(progress * Math.PI);
        currentModel.rotation = rotation * wave;
        currentModel.x = baseModelX + offsetX * wave;
    });
}

function animateHiyoriWave() {
    if (!currentModel) return;
    console.log('ACTION: hiyoriWave');

    animateModelTransform(1200, (progress) => {
        const wave = Math.sin(progress * Math.PI * 2);
        const rise = Math.sin(progress * Math.PI);
        currentModel.x = baseModelX + 40 * wave;
        currentModel.y = baseModelY - 18 * rise;
        currentModel.rotation = 0.26 * wave;
        currentModel.skew.set(0.14 * wave, 0);
        currentModel.scale.set(currentScale * (1 + 0.08 * rise), currentScale * (1 - 0.04 * rise));
    });
}

function animateHiyoriReject() {
    if (!currentModel) return;
    console.log('ACTION: hiyoriReject');

    animateModelTransform(980, (progress) => {
        const shake = Math.sin(progress * Math.PI * 4);
        const rise = Math.sin(progress * Math.PI);
        currentModel.x = baseModelX + 28 * shake;
        currentModel.y = baseModelY + 24 * rise;
        currentModel.rotation = 0.18 * shake;
        currentModel.skew.set(-0.12 * shake, 0);
        currentModel.scale.set(currentScale * (1 + 0.05 * rise), currentScale * (1 - 0.1 * rise));
    });
}

function animateHiyoriChinRest() {
    if (!currentModel) return;
    console.log('ACTION: hiyoriChinRest');

    animateModelTransform(1500, (progress) => {
        const rise = Math.sin(progress * Math.PI);
        currentModel.x = baseModelX - 28 * rise;
        currentModel.y = baseModelY + 16 * rise;
        currentModel.rotation = -0.2 * rise;
        currentModel.skew.set(-0.08 * rise, 0);
        currentModel.scale.set(currentScale * (1 + 0.03 * rise), currentScale * (1 - 0.04 * rise));
    });
}

function animateHiyoriCrouch() {
    if (!currentModel) return;
    console.log('ACTION: hiyoriCrouch');

    animateModelTransform(1200, (progress) => {
        const dip = Math.sin(progress * Math.PI);
        currentModel.y = baseModelY + 82 * dip;
        currentModel.rotation = -0.08 * dip;
        currentModel.scale.set(currentScale * (1 + 0.12 * dip), currentScale * (1 - 0.28 * dip));
    });
}

function getHiyoriActionHandlers(): Record<HiyoriAction, HiyoriActionHandler> {
    return {
        nod: () => {
            animateNod();
            animateHeadTilt(-0.2, -26, 980);
        },
        shake: () => {
            animateShakeHead();
            animateBodyBounce(24, 0, 0.1, 900);
        },
        chinRest: () => {
            animateHiyoriChinRest();
            animateChinRest();
        },
        wave: () => {
            animateHiyoriWave();
            void playMotionByCandidates(['Flick', 'Flick@Body']);
        },
        reject: () => {
            animateHiyoriReject();
            animateShakeHead();
        },
        crouch: () => {
            animateHiyoriCrouch();
            animateCrouchLike();
        },
    };
}

function triggerHiyoriAction(action: HiyoriAction) {
    const handlers = getHiyoriActionHandlers();
    const handler = handlers[action];
    if (!handler) return;
    console.log(`ACTION: hiyori-${action}-module`);
    showActionIndicator(HIYORI_ACTIONS[action].label, HIYORI_ACTIONS[action].durationMs);
    handler();
}

function showActionIndicator(label: string, durationMs: number) {
    const indicator = document.getElementById('action-indicator');
    if (!indicator) return;

    if (actionIndicatorTimer !== null) {
        window.clearTimeout(actionIndicatorTimer);
        actionIndicatorTimer = null;
    }

    indicator.textContent = label;
    indicator.classList.add('visible');
    actionIndicatorTimer = window.setTimeout(() => {
        indicator.classList.remove('visible');
        actionIndicatorTimer = null;
    }, Math.max(500, durationMs - 120));
}

async function playMotionFromGroups(groups: string[]) {
    if (!currentModel) return false;

    const group = getRandomItem(groups);
    if (group === null) return false;

    try {
        return await currentModel.motion(group);
    } catch (error) {
        console.debug('Motion playback failed.', error);
        return false;
    }
}

async function playMotionByCandidates(candidates: string[]) {
    if (!currentModel || candidates.length === 0) {
        return false;
    }

    for (const candidate of candidates) {
        try {
            const ok = await currentModel.motion(candidate);
            if (ok) {
                return true;
            }
        } catch {
            // Try next candidate.
        }
    }

    return false;
}

async function playRandomExpression() {
    if (!currentModel || !getCurrentBehavior().supportsRandomExpression) {
        return false;
    }

    try {
        return await currentModel.expression();
    } catch (error) {
        console.debug('Expression playback failed.', error);
        return false;
    }
}

async function playExpressionByCandidates(candidates: string[]) {
    if (!currentModel || candidates.length === 0) {
        return false;
    }

    for (const candidate of candidates) {
        try {
            const ok = await currentModel.expression(candidate);
            if (ok) {
                return true;
            }
        } catch {
            // Fall through to next candidate.
        }
    }

    return false;
}

function animateFocus(x: number, y: number, duration = 1400) {
    if (!currentModel?.focus) return;
    currentModel.focus(x, y, false);
    window.setTimeout(() => currentModel?.focus?.(app.screen.width / 2, app.screen.height * 0.35, false), duration);
}

async function triggerIdleAction() {
    if (!currentModel || live2dDebugState.talkingActive) return;

    const behavior = getCurrentBehavior();
    const roll = Math.random();

    if (roll < 0.45) {
        await playMotionFromGroups(behavior.idleGroups);
    } else if (roll < 0.75) {
        animateFocus(
            app.screen.width * (0.4 + Math.random() * 0.2),
            app.screen.height * (0.24 + Math.random() * 0.1),
        );
    } else {
        await playRandomExpression();
    }
}

function scheduleIdleLoop() {
    if (!currentModel) return;

    live2dDebugState.idleActive = true;
    const nextDelay = 4500 + Math.random() * 4500;
    idleActionTimer = window.setTimeout(async () => {
        await triggerIdleAction();
        scheduleIdleLoop();
    }, nextDelay);
}

function startTalkingAnimation(text: string) {
    const duration = Math.min(5000, Math.max(900, text.length * 90));

    if (talkLoopTimer !== null) {
        window.clearInterval(talkLoopTimer);
        talkLoopTimer = null;
    }
    if (talkStopTimer !== null) {
        window.clearTimeout(talkStopTimer);
    }

    const sessionId = ++talkingSessionId;
    setCompanionState('talking');

    if (!currentModel) {
        talkStopTimer = window.setTimeout(() => {
            if (sessionId !== talkingSessionId) return;
            talkStopTimer = null;
            setCompanionState('idle');
        }, duration);
        return;
    }

    live2dDebugState.talkingActive = true;

    const behavior = getCurrentBehavior();
    void playMotionFromGroups(behavior.talkGroups);
    void playRandomExpression();

    talkLoopTimer = window.setInterval(() => {
        setLipSyncValue(0.2 + Math.random() * 0.8);
    }, 120);

    talkStopTimer = window.setTimeout(() => {
        if (sessionId !== talkingSessionId) return;
        if (talkLoopTimer !== null) {
            window.clearInterval(talkLoopTimer);
            talkLoopTimer = null;
        }
        talkStopTimer = null;
        setLipSyncValue(0);
        live2dDebugState.talkingActive = false;
        setCompanionState('idle');
    }, duration);
}

async function triggerCharacterAttention() {
    const behavior = getCurrentBehavior();
    await playMotionFromGroups(behavior.tapGroups.length > 0 ? behavior.tapGroups : behavior.greetGroups);
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.28, 1200);
}

function detectCharacterRegion(localX: number, localY: number, width: number, height: number): CharacterRegion {
    const x = width > 0 ? localX / width : 0.5;
    const y = height > 0 ? localY / height : 0.5;

    if (y < 0.24 && x >= 0.28 && x <= 0.72) {
        return 'face';
    }

    if (y >= 0.24 && y < 0.44 && x >= 0.34 && x <= 0.66) {
        return 'chest';
    }

    if (y >= 0.24 && y < 0.68 && (x < 0.28 || x > 0.72)) {
        return 'arms';
    }

    if (y >= 0.44 && y < 0.64 && x >= 0.34 && x <= 0.66) {
        return 'belly';
    }

    return 'legs';
}

async function triggerFaceReaction() {
    console.log(`ACTION: region-face for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const changed = await playExpressionByCandidates(['Surprised.exp3.json', 'Smile.exp3.json', 'f01.exp3.json']);
        if (!changed) {
            await playMotionByCandidates(['Tap', 'Idle']);
        }
    } else if (isHiyoriCharacter()) {
        // Keep region click feedback, but disable Hiyori action playback for now.
    } else {
        await playMotionByCandidates(['']);
        setLipSyncValue(0.35);
        window.setTimeout(() => setLipSyncValue(0), 260);
    }
    animateFocus(app.screen.width * 0.44, app.screen.height * 0.2, 1600);
}

async function triggerChestReaction() {
    console.log(`ACTION: region-chest for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const changed = await playExpressionByCandidates(['Blushing.exp3.json', 'Surprised.exp3.json', 'Smile.exp3.json']);
        if (!changed) {
            await playMotionByCandidates(['Tap']);
        }
    } else if (isHiyoriCharacter()) {
        // Keep region click feedback, but disable Hiyori action playback for now.
    } else {
        await playMotionByCandidates(['']);
    }
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.34, 1400);
}

async function triggerArmsReaction() {
    console.log(`ACTION: region-arms for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const moved = await playMotionByCandidates(['Flick', 'Tap']);
        if (!moved) {
            await playExpressionByCandidates(['Smile.exp3.json', 'Normal.exp3.json']);
        }
    } else if (isHiyoriCharacter()) {
        // Keep region click feedback, but disable Hiyori action playback for now.
    } else {
        await playMotionByCandidates(['']);
    }
    animateFocus(app.screen.width * 0.56, app.screen.height * 0.36, 1200);
}

async function triggerBellyReaction() {
    console.log(`ACTION: region-belly for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const changed = await playExpressionByCandidates(['Sad.exp3.json', 'Angry.exp3.json', 'Blushing.exp3.json']);
        if (!changed) {
            await playMotionByCandidates(['Tap']);
        }
    } else if (isHiyoriCharacter()) {
        // Keep region click feedback, but disable Hiyori action playback for now.
    } else {
        await playMotionByCandidates(['']);
        setLipSyncValue(0.55);
        window.setTimeout(() => setLipSyncValue(0), 320);
    }
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.48, 1400);
}

async function triggerLegsReaction() {
    console.log(`ACTION: region-legs for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const moved = await playMotionByCandidates(['Idle', 'Tap']);
        if (!moved) {
            await playExpressionByCandidates(['Normal.exp3.json', 'Smile.exp3.json']);
        }
    } else if (isHiyoriCharacter()) {
        // Keep region click feedback, but disable Hiyori action playback for now.
    } else {
        await playMotionByCandidates(['']);
    }
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.62, 1000);
}

async function triggerRegionReaction(region: CharacterRegion) {
    switch (region) {
        case 'face':
            await triggerFaceReaction();
            break;
        case 'chest':
            await triggerChestReaction();
            break;
        case 'arms':
            await triggerArmsReaction();
            break;
        case 'belly':
            await triggerBellyReaction();
            break;
        case 'legs':
        default:
            await triggerLegsReaction();
            break;
    }
}

declare global {
    interface Window {
        Live2DCubismCore?: unknown;
        __live2dDebugState?: typeof live2dDebugState;
    }
}

window.__live2dDebugState = live2dDebugState;
live2dDebugState.hiyoriActions = Object.fromEntries(
    HIYORI_ACTION_KEYS.map((key) => [key, HIYORI_ACTIONS[key].label]),
) as Record<HiyoriAction, string>;

async function ensureCubismCore() {
    if (window.Live2DCubismCore) {
        return;
    }

    await new Promise<void>((resolve, reject) => {
        const existing = document.querySelector<HTMLScriptElement>('script[data-live2d-core="true"]');
        if (existing) {
            if (existing.dataset.loadState === 'failed') {
                existing.remove();
            } else {
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', () => reject(new Error('Live2D Cubism Core script failed to load.')), { once: true });
                return;
            }
        }

        const script = document.createElement('script');
        script.src = cubismCoreUrl;
        script.async = true;
        script.dataset.live2dCore = 'true';
        script.dataset.loadState = 'loading';
        script.onload = () => {
            script.dataset.loadState = 'loaded';
            resolve();
        };
        script.onerror = () => {
            script.dataset.loadState = 'failed';
            reject(new Error('Live2D Cubism Core script failed to load.'));
        };
        document.head.appendChild(script);
    });

    if (!window.Live2DCubismCore) {
        throw new Error('Live2D Cubism Core did not initialize.');
    }
}

// ============== PIXI + Live2D 初始化 ==============

async function initPixi() {
    // 创建 PIXI 应用
    (window as Window & { PIXI?: typeof PIXI }).PIXI = PIXI;
    await loadAppSettings({ preserveBootstrapCompanion: true });
    updateCharacterLabel();
    syncCompanionSettingsForm();

    app = new PIXI.Application({
        width: BASE_WINDOW_WIDTH,
        height: BASE_WINDOW_HEIGHT,
        backgroundColor: 0x000000,
        backgroundAlpha: 0, // 透明背景
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
    });

    // 将 canvas 添加到页面
    const canvas = document.getElementById('character-canvas') as HTMLDivElement | null;
    if (canvas) {
        canvas.appendChild(app.view as HTMLCanvasElement);
        (app.view as HTMLCanvasElement).style.width = '100%';
        (app.view as HTMLCanvasElement).style.height = '100%';
    }

    // 加载 Live2D 模型
    await loadLive2DModel();
}

async function enterDesktopFlow() {
    if (desktopFlowStarted) {
        return;
    }

    setCompanionState('idle');
    try {
        await initPixi();
        desktopFlowStarted = true;
    } catch (error) {
        desktopFlowStarted = false;
        throw error;
    }
}

async function loadLive2DModel() {
    const modelPath = live2dModels[currentCharacter] ?? live2dModels.kei;

    try {
        clearActionTimers();
        await ensureCubismCore();
        const { Live2DModel } = await import('pixi-live2d-display/cubism4');

        // 使用 pixi-live2d-display 加载模型
        currentModel = await Live2DModel.from(modelPath, {
            autoInteract: false,
            autoDrag: false,
        });

        // 设置模型位置和大小
        currentModel.x = 0;
        currentModel.y = 0;
        currentModel.scale.set(1);

        currentScale = appSettings.character_scales[currentCharacter] ?? 1;

        // 添加到场景
        if (app.stage.children.length > 0) {
            app.stage.removeChildren();
        }
        app.stage.addChild(currentModel);

        applyCurrentScale();
        updateCharacterLabel();
        updateScaleControls();
        live2dDebugState.currentCharacter = currentCharacter;

        void playMotionFromGroups(getCurrentBehavior().greetGroups);
        scheduleIdleLoop();

        console.log('✅ Live2D 模型加载成功');
    } catch (error) {
        console.error('❌ Live2D 模型加载失败:', error);
        // 降级方案：显示占位角色
        showPlaceholderCharacter();
    }
}

function showPlaceholderCharacter() {
    // 简单的 PIXI 图形作为占位
    const graphics = new PIXI.Graphics();
    graphics.beginFill(0xFFB6C1);
    graphics.drawCircle(200, 400, 100);
    graphics.endFill();
    app.stage.addChild(graphics);
}

function bindCharacterInteractions() {
    const hitArea = document.getElementById('character-hit-area');
    if (!hitArea) return;

    const dragThreshold = 6;

    const onPointerMove = async (event: PointerEvent) => {
        if (!pointerDown) return;

        const moved = Math.hypot(event.screenX - pointerStartX, event.screenY - pointerStartY);
        if (!dragStarted && moved < dragThreshold) return;

        dragStarted = true;

        try {
            await getCurrentWindow().setPosition(
                new PhysicalPosition(
                    Math.round(windowStartX + (event.screenX - pointerStartX)),
                    Math.round(windowStartY + (event.screenY - pointerStartY)),
                ),
            );
        } catch (error) {
            console.debug('Window drag move failed.', error);
        }
    };

    const stopPointerTracking = () => {
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onPointerUp);
    };

    const onPointerUp = () => {
        if (pointerDown && !dragStarted) {
            const region = detectCharacterRegion(pointerLocalX, pointerLocalY, hitArea.clientWidth || 1, hitArea.clientHeight || 1);
            console.log(`🎯 点击区域: ${region}`);
            void handleCompanionSingleClick(region);
        }

        pointerDown = false;
        dragStarted = false;
        stopPointerTracking();
    };

    hitArea.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        pointerDown = true;
        dragStarted = false;
        pointerStartX = event.screenX;
        pointerStartY = event.screenY;
        const rect = hitArea.getBoundingClientRect();
        pointerLocalX = event.clientX - rect.left;
        pointerLocalY = event.clientY - rect.top;

        void getCurrentWindow().outerPosition().then((position) => {
            windowStartX = position.x;
            windowStartY = position.y;
        });
        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
    });

    hitArea.addEventListener('dblclick', () => {
        void openChat();
    });

    const bubble = document.getElementById('reaction-bubble');
    bubble?.addEventListener('click', () => {
        void openChat();
    });
}

// ============== 聊天窗口 ==============

async function openChat() {
    hideReactionBubble();
    try {
        await ensureChatHistoryLoaded();
    } catch (error) {
        console.warn('加载聊天记录失败，将在下次打开时重试。', error);
    }

    const chatWindow = document.getElementById('chat-window');
    if (chatWindow) {
        chatWindow.classList.add('visible');
        chatWindowVisible = true;
    }
    logProductEvent('chat_opened', { character: currentCharacter });
}

function closeChat() {
    const chatWindow = document.getElementById('chat-window');
    if (chatWindow) {
        chatWindow.classList.remove('visible');
        chatWindowVisible = false;
    }
}

function openSettingsPanel() {
    const panel = document.getElementById('settings-panel');
    if (panel) {
        panel.classList.add('visible');
    }
    updateCharacterLabel();
    updateScaleControls();
    syncCompanionSettingsForm();
    void refreshCompanionList();
    logProductEvent('settings_opened', { character: currentCharacter });
    void refreshMemoryList();
}

function closeSettingsPanel() {
    const panel = document.getElementById('settings-panel');
    if (panel) {
        panel.classList.remove('visible');
    }
}

function bindDraggablePanel(panelSelector: string, handleSelector: string) {
    const panel = document.querySelector<HTMLElement>(panelSelector);
    const handle = document.querySelector<HTMLElement>(handleSelector);
    if (!panel || !handle) return;

    let dragging = false;
    let startX = 0;
    let startY = 0;
    let originLeft = 0;
    let originTop = 0;

    const onMove = (event: PointerEvent) => {
        if (!dragging) return;
        const nextLeft = originLeft + (event.clientX - startX);
        const nextTop = originTop + (event.clientY - startY);
        panel.style.left = `${nextLeft}px`;
        panel.style.top = `${nextTop}px`;
        panel.style.right = 'auto';
        panel.style.bottom = 'auto';
    };

    const stopDragging = () => {
        dragging = false;
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', stopDragging);
    };

    handle.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        if ((event.target as HTMLElement).closest('button')) return;

        dragging = true;
        startX = event.clientX;
        startY = event.clientY;
        const rect = panel.getBoundingClientRect();
        originLeft = rect.left;
        originTop = rect.top;
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', stopDragging);
    });
}

function toggleChat() {
    if (chatWindowVisible) {
        closeChat();
    } else {
        void openChat();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input') as HTMLTextAreaElement;
    if (!input) return;

    const text = input.value.trim();
    if (!text) return;

    input.value = '';

    setCompanionState('listening');
    addMessage('user', text);
    logProductEvent('message_sent', { length: text.length, character: currentCharacter });
    void triggerCharacterAttention();

    try {
        setCompanionState('thinking');
        const response = await chatClient.sendAndReturn(text);
        addMessage('assistant', response.content);
        startTalkingAnimation(response.content);
    } catch (error) {
        console.error('❌ 发送消息失败:', error);
        setCompanionState('idle');
        addMessage('assistant', '抱歉，我遇到了一些问题，请稍后再试。');
    }
}

function addMessage(role: string, content: string) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // 滚动到底部
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function ensureChatHistoryLoaded() {
    if (chatHistoryLoaded) {
        return;
    }

    if (chatHistoryLoadPromise) {
        return chatHistoryLoadPromise;
    }

    chatHistoryLoadPromise = (async () => {
        const history = await chatClient.loadHistory();
        renderChatHistory(history);
        chatHistoryLoaded = true;
        logProductEvent('history_restored', { count: history.length });
    })().catch((error) => {
        chatHistoryLoaded = false;
        throw error;
    }).finally(() => {
        chatHistoryLoadPromise = null;
    });

    return chatHistoryLoadPromise;
}

function renderChatHistory(messages: ChatMessage[]) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

    messagesContainer.innerHTML = '';
    messages.forEach((message) => addMessage(message.role, message.content));
}

function renderMemoryList(memories: MemoryItem[]) {
    const container = document.getElementById('memory-list');
    if (!container) return;

    container.innerHTML = '';

    if (memories.length === 0) {
        container.textContent = '暂时还没有记住新的内容。';
        return;
    }

    memories.forEach((memory) => {
        const row = document.createElement('div');
        row.className = 'memory-row';

        const text = document.createElement('span');
        text.textContent = memory.content;

        const button = document.createElement('button');
        button.dataset.memoryId = String(memory.id);
        button.textContent = '删除';
        button.addEventListener('click', async () => {
            await chatClient.deleteMemory(memory.id);
            logProductEvent('memory_deleted', { id: memory.id });
            await refreshMemoryList();
        });

        row.appendChild(text);
        row.appendChild(button);
        container.appendChild(row);
    });
}

async function refreshMemoryList() {
    const memories = await chatClient.loadMemory();
    logProductEvent('memory_viewed', { count: memories.length });
    renderMemoryList(memories);
}

function renderBuiltInModelList(importedModels: ImportedModelItem[] = []) {
    const list = document.getElementById('builtin-model-list');
    if (!list) return;

    list.innerHTML = '';
    Object.keys(live2dModels)
        .filter((key) => !importedModelKeys.has(key))
        .forEach((key) => {
            list.appendChild(
                buildModelCard(
                    getCharacterDisplayName(key),
                    key === currentCharacter ? '当前使用中' : '可用模型',
                    key,
                    live2dModels[key],
                ),
            );
        });

    importedModels.forEach((model) => {
        const key = getImportedModelKey(model);
        list.appendChild(
            buildModelCard(
                model.name,
                key === currentCharacter ? '当前使用中' : '可用模型',
                key,
                model.model_path,
            ),
        );
    });
}

async function refreshModelPanel() {
    const imported = await chatClient.loadImportedModels();
    syncImportedModelRegistry(imported);

    const summary = document.getElementById('active-model-summary');
    if (summary) {
        summary.textContent = `${appSettings.character_name} · ${getCharacterDisplayName(currentCharacter)}`;
    }

    renderBuiltInModelList(imported);
}

function openModelPanel() {
    const panel = document.getElementById('model-panel');
    if (panel) {
        panel.classList.add('visible');
    }
    void refreshModelPanel();
}

function closeModelPanel() {
    const panel = document.getElementById('model-panel');
    if (panel) {
        panel.classList.remove('visible');
    }
}

async function promptImportModel() {
    const modelPath = window.prompt('请输入已解压模型的 model3.json 完整路径');
    if (!modelPath) return;

    const name = modelPath.split(/[/\\]/).slice(-2, -1)[0] || 'Imported Model';
    try {
        await chatClient.importModel({ name, model_path: modelPath });
        await refreshModelPanel();
    } catch (error) {
        console.error('Failed to import model.', error);
        alert('导入模型失败，请确认你提供的是已解压的 model3.json 路径。');
    }
}

// ============== 右键菜单 ==============

let contextMenuVisible = false;

function showContextMenu(x: number, y: number) {
    const menu = document.getElementById('context-menu');
    if (menu) {
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        menu.classList.add('visible');
        contextMenuVisible = true;
    }
}

function hideContextMenu() {
    const menu = document.getElementById('context-menu');
    if (menu) {
        menu.classList.remove('visible');
        contextMenuVisible = false;
    }
}

function switchCharacter(name: string) {
    console.log('🎭 切换角色:', name);
    hideContextMenu();
    if (!live2dModels[name]) {
        console.warn('Unknown Live2D character:', name);
        return;
    }

    currentCharacter = name;
    void loadLive2DModel();
    void saveAppSettings();
}

function bindContextMenuActions() {
    const menu = document.getElementById('context-menu');
    if (!menu) return;

    const modelPickerButton = menu.querySelector<HTMLElement>('[data-action="model-picker"]');
    modelPickerButton?.addEventListener('click', () => {
        hideContextMenu();
        openModelPanel();
    });

    const hideButton = menu.querySelector<HTMLElement>('[data-action="hide"]');
    hideButton?.addEventListener('click', toggleCharacterVisibility);

    const settingsButton = menu.querySelector<HTMLElement>('[data-action="settings"]');
    settingsButton?.addEventListener('click', showSettings);

    const quitButton = menu.querySelector<HTMLElement>('[data-action="quit"]');
    quitButton?.addEventListener('click', quitApp);
}

function toggleCharacterVisibility() {
    hideContextMenu();
    characterHidden = true;
    updateHideMenuLabel();
    invoke('hide_main_window');
}

function showSettings() {
    console.log('⚙️ 打开设置');
    hideContextMenu();
    openSettingsPanel();
}

function quitApp() {
    console.log('❌ 退出应用');
    hideContextMenu();
    // 调用 Tauri API 退出
    invoke('quit_app');
}

// ============== 事件绑定 ==============

// 右键菜单
document.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    showContextMenu(e.clientX, e.clientY);
});

// 点击其他地方关闭菜单
document.addEventListener('click', (e) => {
    const menu = document.getElementById('context-menu');
    if (menu && !menu.contains(e.target as Node)) {
        hideContextMenu();
    }
});

document.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    const menu = document.getElementById('context-menu');
    if (menu && !menu.contains(e.target as Node)) {
        hideContextMenu();
    }
});

// Enter 发送
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        const input = document.getElementById('chat-input') as HTMLTextAreaElement;
        if (document.activeElement === input) {
            e.preventDefault();
            sendMessage();
        }
    }
});

// ============== 初始化 ==============

window.addEventListener('DOMContentLoaded', async () => {
    bindContextMenuActions();
    bindCharacterInteractions();
    bindFirstRunCreator();

    // 绑定聊天窗口关闭按钮
    const closeBtn = document.querySelector('.close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeChat);
    }

    // 绑定发送按钮
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    const settingsCloseBtn = document.querySelector('.settings-close-btn');
    if (settingsCloseBtn) {
        settingsCloseBtn.addEventListener('click', closeSettingsPanel);
    }

    const modelCloseBtn = document.querySelector('.model-close-btn');
    if (modelCloseBtn) {
        modelCloseBtn.addEventListener('click', closeModelPanel);
    }

    const importModelBtn = document.getElementById('import-model-btn');
    importModelBtn?.addEventListener('click', () => {
        void promptImportModel();
    });

    bindDraggablePanel('#chat-window', '.chat-header');
    bindDraggablePanel('#settings-panel', '.settings-header');

    bindCompanionSettingsForm();

    const scaleSlider = document.getElementById('scale-slider') as HTMLInputElement | null;
    scaleSlider?.addEventListener('input', (event) => {
        const target = event.target as HTMLInputElement;
        void setScale(Number(target.value), false);
    });
    scaleSlider?.addEventListener('change', (event) => {
        const target = event.target as HTMLInputElement;
        void setScale(Number(target.value), true);
    });

    const scaleDecreaseBtn = document.getElementById('scale-decrease-btn');
    scaleDecreaseBtn?.addEventListener('click', () => void setScale(currentScale - 0.05));

    const scaleIncreaseBtn = document.getElementById('scale-increase-btn');
    scaleIncreaseBtn?.addEventListener('click', () => void setScale(currentScale + 0.05));

    const scaleResetBtn = document.getElementById('scale-reset-btn');
    scaleResetBtn?.addEventListener('click', () => void setScale(autoFitScale));

    updateHideMenuLabel();
    updateChatTitle();
    syncCompanionSettingsForm();
    hideBootstrapError();

    try {
        await refreshModelPanel();
        await determineCompanionBootstrapState();
        if (firstRunRequired) {
            showFirstRunPanel();
            return;
        }

        hideFirstRunPanel();
        await enterDesktopFlow();
    } catch (error) {
        console.error('Failed to determine companion bootstrap state.', error);
        hideFirstRunPanel();
        showBootstrapError('伙伴加载失败，请确认后端服务可用后再重试。');
    }
});
