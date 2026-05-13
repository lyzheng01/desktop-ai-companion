/**
 * Desktop AI Companion - 主入口
 * Live2D 角色渲染 + 聊天交互
 */

import * as PIXI from 'pixi.js';
import { invoke } from '@tauri-apps/api/core';
import { ChatClient, type ChatMessage } from './chat-client';

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
type HiyoriAction = 'nod' | 'shake' | 'chinRest' | 'wave' | 'reject' | 'crouch';
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
const chatClient = new ChatClient({
    apiEndpoint: 'http://localhost:8080/chat',
});
const cubismCoreUrl = 'https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js';
const live2dModels: Record<string, string> = {
    kei: '/live2d/kei_en/kei_basic_free/runtime/kei_basic_free.model3.json',
    chitose: '/live2d/chitose/chitose_t02.model3.json',
    hiyori: '/live2d/hiyori/hiyori_pro_jp.model3.json',
};
let currentCharacter = 'kei';
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
let appSettings: AppSettings = {
    user_nickname: '小伙伴',
    user_display_name: '你',
    character_type: 'kei',
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
};

function setCompanionState(state: CompanionState) {
    document.body.dataset.companionState = state;
    console.log(`COMPANION_STATE: ${state}`);
}

async function loadAppSettings() {
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
    const labels: Record<string, string> = {
        kei: 'Kei',
        chitose: 'Chitose',
        hiyori: 'Hiyori',
    };
    return labels[name] ?? name;
}

function getCurrentBehavior() {
    return characterBehaviors[currentCharacter] ?? characterBehaviors.kei;
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

function applyCurrentScale() {
    if (!currentModel) return;
    currentModel.scale.set(currentScale, currentScale);
    baseModelX = (app.screen.width - currentModel.width) / 2;
    baseModelY = app.screen.height - currentModel.height;
    currentModel.x = baseModelX;
    currentModel.y = baseModelY;
    currentModel.rotation = 0;
    currentModel.skew.set(0, 0);
    updateScaleControls();
}

function setScale(scale: number, persist = true) {
    currentScale = Math.min(1.4, Math.max(0.01, scale));
    appSettings.character_scales[currentCharacter] = currentScale;
    applyCurrentScale();
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
            runHiyoriStageAction(1500, (progress, stage) => {
                const hold = Math.sin(progress * Math.PI);
                stage.style.transform = `translate3d(${-22 * hold}px, ${14 * hold}px, 0) rotate(${-9 * hold}deg) scale(${1 + 0.02 * hold}, ${1 - 0.03 * hold})`;
                setModelParameter(angleX, -16 * hold);
                setModelParameter(angleY, 10 * hold);
                setModelParameter(angleZ, -18 * hold);
            }, () => {
                setModelParameter(angleX, 0);
                setModelParameter(angleY, 0);
                setModelParameter(angleZ, 0);
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
            runHiyoriStageAction(1200, (progress, stage) => {
                const dip = Math.sin(progress * Math.PI);
                stage.style.transform = `translate3d(0, ${74 * dip}px, 0) scale(${1 + 0.12 * dip}, ${1 - 0.28 * dip}) rotate(${-4 * dip}deg)`;
                setModelParameter(bodyX, 8 * dip);
            }, () => {
                setModelParameter(bodyX, 0);
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
    } else if (currentCharacter === 'hiyori') {
        playHiyoriAction('nod');
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
    } else if (currentCharacter === 'hiyori') {
        playHiyoriAction('chinRest');
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
    } else if (currentCharacter === 'hiyori') {
        playHiyoriAction('wave');
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
    } else if (currentCharacter === 'hiyori') {
        playHiyoriAction('reject');
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
    } else if (currentCharacter === 'hiyori') {
        playHiyoriAction('crouch');
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

async function ensureCubismCore() {
    if (window.Live2DCubismCore) {
        return;
    }

    await new Promise<void>((resolve, reject) => {
        const existing = document.querySelector<HTMLScriptElement>('script[data-live2d-core="true"]');
        if (existing) {
            existing.addEventListener('load', () => resolve(), { once: true });
            existing.addEventListener('error', () => reject(new Error('Live2D Cubism Core script failed to load.')), { once: true });
            return;
        }

        const script = document.createElement('script');
        script.src = cubismCoreUrl;
        script.async = true;
        script.dataset.live2dCore = 'true';
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Live2D Cubism Core script failed to load.'));
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
    await loadAppSettings();

    app = new PIXI.Application({
        width: 400,
        height: 600,
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

        autoFitScale = Math.min(
            (app.screen.width * 0.9) / currentModel.width,
            (app.screen.height * 0.92) / currentModel.height,
        );

        currentScale = appSettings.character_scales[currentCharacter] ?? autoFitScale;

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
    hitArea.setAttribute('data-tauri-drag-region', '');

    hitArea.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        pointerDown = true;
        dragStarted = false;
        pointerStartX = event.screenX;
        pointerStartY = event.screenY;
        const rect = hitArea.getBoundingClientRect();
        pointerLocalX = event.clientX - rect.left;
        pointerLocalY = event.clientY - rect.top;
    });

    hitArea.addEventListener('pointermove', (event) => {
        if (!pointerDown) return;

        const moved = Math.hypot(event.screenX - pointerStartX, event.screenY - pointerStartY);
        if (!dragStarted && moved < dragThreshold) return;

        dragStarted = true;
    });

    hitArea.addEventListener('pointerup', () => {
        if (pointerDown && !dragStarted) {
            const region = detectCharacterRegion(pointerLocalX, pointerLocalY, hitArea.clientWidth || 1, hitArea.clientHeight || 1);
            console.log(`🎯 点击区域: ${region}`);
            void triggerRegionReaction(region);
            window.setTimeout(() => void openChat(), 260);
        }

        pointerDown = false;
        dragStarted = false;
    });

    hitArea.addEventListener('pointerleave', () => {
        if (!dragStarted) {
            pointerDown = false;
        }
    });
}

// ============== 聊天窗口 ==============

async function openChat() {
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

    menu.querySelectorAll<HTMLElement>('[data-character]').forEach((button) => {
        button.addEventListener('click', () => {
            const name = button.dataset.character;
            if (name) {
                switchCharacter(name);
            }
        });
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
    const container = document.getElementById('character-container');
    if (container) {
        characterHidden = !characterHidden;
        container.style.display = characterHidden ? 'none' : 'block';
        updateHideMenuLabel();
    }
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

window.addEventListener('DOMContentLoaded', () => {
    setCompanionState('idle');
    initPixi();
    bindContextMenuActions();
    bindCharacterInteractions();

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

    bindDraggablePanel('#chat-window', '.chat-header');
    bindDraggablePanel('#settings-panel', '.settings-header');

    bindCompanionSettingsForm();

    const scaleSlider = document.getElementById('scale-slider') as HTMLInputElement | null;
    scaleSlider?.addEventListener('input', (event) => {
        const target = event.target as HTMLInputElement;
        setScale(Number(target.value), false);
    });
    scaleSlider?.addEventListener('change', (event) => {
        const target = event.target as HTMLInputElement;
        setScale(Number(target.value), true);
    });

    const scaleDecreaseBtn = document.getElementById('scale-decrease-btn');
    scaleDecreaseBtn?.addEventListener('click', () => setScale(currentScale - 0.05));

    const scaleIncreaseBtn = document.getElementById('scale-increase-btn');
    scaleIncreaseBtn?.addEventListener('click', () => setScale(currentScale + 0.05));

    const scaleResetBtn = document.getElementById('scale-reset-btn');
    scaleResetBtn?.addEventListener('click', () => setScale(autoFitScale));

    updateHideMenuLabel();
    updateChatTitle();
    syncCompanionSettingsForm();
});
