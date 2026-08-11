import { makeAutoObservable, observable, runInAction } from 'mobx';

export type ScenarioStatus = 'success' | 'warning' | 'alert';

export type OperatingState = 'running' | 'stopped';

export interface Parameter {
  parameterId: string;
  tag: string;
  name: string;
  valuePercent: number;
  status: ScenarioStatus;
}

export interface ScenarioComponent {
  componentId: string;
  uiId: string;
  tag: string;
  name: string;
  componentType: string;
  status: ScenarioStatus;
  operatingState?: OperatingState;
  parameters: Parameter[];
  state?: Record<string, unknown>;
}

export interface JournalEntry {
  entryId: string;
  time: string;
  description: string;
}

export interface Timing {
  mode: string;
  elapsedMs: number;
  totalMs: number;
  remainingMs: number;
  progressPercent: number;
}

export interface ChartPoint {
  time: number;
  value: number;
}

interface TelemetryMessage {
  type: 'telemetry.snapshot' | 'telemetry.update';

  sessionId: string;
  sequenceNo: number;
  stateVersion: number;

  timing: Timing;
  components: ScenarioComponent[];
  journal: JournalEntry[];
}

interface ActionResultMessage {
  type: 'action.result';
  status: 'accepted' | 'rejected';
  actionId?: string;
  stateVersion?: number;

  error?: {
    code: string;
    message: string;
  };
}

export interface ScenarioHintMessage {
  type: 'scenario.hint';
  sessionId: string;
  virtualTimeMs: number;
  hintId: string;
  level: ScenarioStatus;
  title: string;
  message: string;
  displayDurationMs: number;
}

type WebSocketMessage = TelemetryMessage | ActionResultMessage | ScenarioHintMessage;

class SimulatorStore {
  socket: WebSocket | null = null;

  selectedElementId: string | null = null;

  timing: Timing = {
    mode: 'live',
    elapsedMs: 0,
    totalMs: 120000,
    remainingMs: 120000,
    progressPercent: 0,
  };

  components: ScenarioComponent[] = [];

  journal: JournalEntry[] = [];

  activeHint: ScenarioHintMessage | null = null;

  private hintTimeoutId: number | null = null;

  history: Record<string, ChartPoint[]> = {};

  lastSequenceNo = -1;

  isConnected = false;

  constructor() {
    makeAutoObservable(this, {
      socket: false,
      history: observable.ref,
    });
  }

  connect = (sessionId: string) => {
    if (this.socket) {
      this.disconnect();
    }

    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/v1/sessions/${sessionId}`);

    this.socket = socket;

    socket.onopen = () => {
      runInAction(() => {
        this.isConnected = true;
      });

      console.log('WebSocket connected');
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;

        if (message.type === 'action.result') {
          this.handleActionResult(message);
          return;
        }

        if (message.type === 'scenario.hint') {
          this.showHint(message);
          return;
        }

        if (message.type === 'telemetry.snapshot' || message.type === 'telemetry.update') {
          this.applyTelemetry(message);
        }
      } catch (error) {
        console.error('WebSocket parse error:', error);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onclose = (event) => {
      runInAction(() => {
        this.isConnected = false;
      });

      console.log('WebSocket closed:', event.code, event.reason);
    };
  };

  disconnect = () => {
    this.socket?.close();
    this.socket = null;
    this.isConnected = false;
    this.dismissHint();
  };

  applyTelemetry = (message: TelemetryMessage) => {
    if (message.type === 'telemetry.update' && message.sequenceNo <= this.lastSequenceNo) {
      return;
    }

    runInAction(() => {
      this.lastSequenceNo = message.sequenceNo;

      this.timing = message.timing;
      this.components = message.components;
      this.journal = message.journal;

      this.updateHistory(message);
    });
  };

  handleActionResult = (message: ActionResultMessage) => {
    if (message.status === 'accepted') {
      console.log('Action accepted:', message);
      return;
    }

    console.error('Action rejected:', message.error);
  };

  showHint = (message: ScenarioHintMessage) => {
    if (this.hintTimeoutId !== null) {
      window.clearTimeout(this.hintTimeoutId);
    }

    this.activeHint = message;
    this.hintTimeoutId = window.setTimeout(() => {
      runInAction(() => {
        if (this.activeHint?.hintId === message.hintId) {
          this.activeHint = null;
        }
        this.hintTimeoutId = null;
      });
    }, message.displayDurationMs);
  };

  dismissHint = () => {
    if (this.hintTimeoutId !== null) {
      window.clearTimeout(this.hintTimeoutId);
      this.hintTimeoutId = null;
    }
    this.activeHint = null;
  };

  sendAction = (actionType: string, targetId?: string, parameters?: Record<string, unknown>) => {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return;
    }

    const message: {
      actionType: string;
      targetId?: string;
      parameters?: Record<string, unknown>;
    } = {
      actionType,
    };

    if (targetId !== undefined) {
      message.targetId = targetId;
    }

    if (parameters !== undefined) {
      message.parameters = parameters;
    }

    this.socket.send(JSON.stringify(message));

    console.log('WebSocket sent:', message);
  };

  setSelectedElement = (uiId: string) => {
    this.selectedElementId = uiId;

    const component = this.components.find((item) => item.uiId === uiId);

    if (!component) {
      return;
    }

    this.sendAction('open_equipment_card', component.componentId);
  };

  get selectedComponent() {
    if (!this.selectedElementId) {
      return null;
    }

    return this.components.find((component) => component.uiId === this.selectedElementId) ?? null;
  }

  getParameter = (parameterId: string) => {
    for (const component of this.components) {
      const parameter = component.parameters.find((item) => item.parameterId === parameterId);

      if (parameter) {
        return parameter;
      }
    }

    return undefined;
  };

  getParameterHistory = (parameterId: string) => {
    return this.history[parameterId] ?? [];
  };

  private updateHistory = (message: TelemetryMessage) => {
    const time = Math.floor(message.timing.elapsedMs / 1000);

    const nextHistory = {
      ...this.history,
    };

    for (const component of message.components) {
      for (const parameter of component.parameters) {
        const currentHistory = [...(nextHistory[parameter.parameterId] ?? [])];

        const lastPoint = currentHistory[currentHistory.length - 1];

        if (lastPoint?.time === time) {
          currentHistory[currentHistory.length - 1] = {
            time,
            value: parameter.valuePercent,
          };
        } else {
          currentHistory.push({
            time,
            value: parameter.valuePercent,
          });
        }

        if (currentHistory.length > 120) {
          currentHistory.shift();
        }

        nextHistory[parameter.parameterId] = currentHistory;
      }
    }

    this.history = nextHistory;
  };

  get formattedElapsedTime() {
    const totalSeconds = Math.floor(this.timing.elapsedMs / 1000);

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }
}

export const simulatorStore = new SimulatorStore();
