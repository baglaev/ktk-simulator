import { makeAutoObservable } from 'mobx';

export interface ChartPoint {
  time: string;
  value: number;
}

class SimulatorStore {
  selectedElementId: string | null = null;

  chartData: ChartPoint[] = [
    { time: '10:00', value: 20 },
    { time: '10:01', value: 25 },
    { time: '10:02', value: 22 },
    { time: '10:03', value: 31 },
    { time: '10:04', value: 28 },
    { time: '10:05', value: 35 },
  ];

  constructor() {
    makeAutoObservable(this);
  }

  setSelectedElement = (id: string) => {
    this.selectedElementId = id;

    // здесь потом будет запрос/WS обновление
    // например:
    // ws.send({ type:'subscribe', element:id })
  };

  updateChart = (data: ChartPoint[]) => {
    this.chartData = data;
  };
}

export const simulatorStore = new SimulatorStore();
