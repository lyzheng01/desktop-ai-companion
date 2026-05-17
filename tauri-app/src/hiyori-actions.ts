export type HiyoriAction = 'nod' | 'shake' | 'chinRest' | 'wave' | 'reject' | 'crouch'

export type HiyoriActionSpec = {
  className: string
  label: string
  durationMs: number
}

export const HIYORI_ACTIONS: Record<HiyoriAction, HiyoriActionSpec> = {
  nod: {
    className: 'action-nod',
    label: '点头',
    durationMs: 1800,
  },
  shake: {
    className: 'action-shake',
    label: '摇头',
    durationMs: 1900,
  },
  chinRest: {
    className: 'action-chinrest',
    label: '托腮',
    durationMs: 2200,
  },
  wave: {
    className: 'action-wave',
    label: '摆手',
    durationMs: 1900,
  },
  reject: {
    className: 'action-reject',
    label: '抗议',
    durationMs: 1800,
  },
  crouch: {
    className: 'action-crouch',
    label: '蹲下',
    durationMs: 2000,
  },
}

export const HIYORI_ACTION_KEYS = Object.keys(HIYORI_ACTIONS) as HiyoriAction[]
