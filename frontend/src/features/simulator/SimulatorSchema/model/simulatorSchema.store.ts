import { makeAutoObservable } from 'mobx';

export interface ChartPoint {
  time: string;
  value: number;
}

export interface Metric {
  id: string;
  title: string;
  unit: string;
  color: string;
  value: number;
  trend: ChartPoint[];
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

  // metrics = [
  //   {
  //     id: 'pressure',
  //     title: 'Давление',
  //     unit: 'МПа',
  //     color: '#2ecc71',
  //     value: 2.8,
  //     trend: [
  //       { time: '1', value: 20 },
  //       { time: '2', value: 21 },
  //       { time: '3', value: 23 },
  //       { time: '4', value: 25 },
  //       { time: '5', value: 27 },
  //       { time: '6', value: 28 },
  //     ],
  //   },
  //   {
  //     id: 'temperature',
  //     title: 'Температура',
  //     unit: '°C',
  //     color: '#e74c3c',
  //     value: 84,
  //     trend: [
  //       { time: '1', value: 88 },
  //       { time: '2', value: 87 },
  //       { time: '3', value: 86 },
  //       { time: '4', value: 85 },
  //       { time: '5', value: 84 },
  //       { time: '6', value: 84 },
  //     ],
  //   },
  // ];

  metrics: Metric[] = [
    {
      id: 'pressure',
      title: 'Давление',
      unit: 'МПа',
      color: '#2ecc71',
      value: 2.8,
      trend: [
        { time: '1', value: 20 },
        { time: '2', value: 21 },
        { time: '3', value: 23 },
        { time: '4', value: 25 },
        { time: '5', value: 27 },
        { time: '6', value: 28 },
      ],
    },

    {
      id: 'temperature',
      title: 'Температура',
      unit: '°C',
      color: '#e74c3c',
      value: 84,
      trend: [
        { time: '1', value: 90 },
        { time: '2', value: 88 },
        { time: '3', value: 87 },
        { time: '4', value: 86 },
        { time: '5', value: 85 },
        { time: '6', value: 84 },
      ],
    },

    {
      id: 'flow',
      title: 'Расход',
      unit: 'м³/ч',
      color: '#2ecc71',
      value: 112,
      trend: [
        { time: '1', value: 90 },
        { time: '2', value: 95 },
        { time: '3', value: 100 },
        { time: '4', value: 105 },
        { time: '5', value: 110 },
        { time: '6', value: 112 },
      ],
    },

    {
      id: 'vibration',
      title: 'Вибрация',
      unit: 'мм/с',
      color: '#e74c3c',
      value: 1.8,
      trend: [
        { time: '1', value: 1 },
        { time: '2', value: 1.2 },
        { time: '3', value: 1.5 },
        { time: '4', value: 1.6 },
        { time: '5', value: 1.7 },
        { time: '6', value: 1.8 },
      ],
    },

    {
      id: 'level',
      title: 'Уровень',
      unit: '%',
      color: '#2ecc71',
      value: 43,
      trend: [
        { time: '1', value: 35 },
        { time: '2', value: 37 },
        { time: '3', value: 39 },
        { time: '4', value: 41 },
        { time: '5', value: 42 },
        { time: '6', value: 43 },
      ],
    },

    {
      id: 'current',
      title: 'Ток двигателя',
      unit: 'А',
      color: '#e74c3c',
      value: 117,
      trend: [
        { time: '1', value: 130 },
        { time: '2', value: 125 },
        { time: '3', value: 122 },
        { time: '4', value: 120 },
        { time: '5', value: 118 },
        { time: '6', value: 117 },
      ],
    },
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

  // updateChart = (data: ChartPoint[]) => {
  //   this.chartData = data;
  // };

  updateMetric = (metricId: string, value: number) => {
    const metric = this.metrics.find((item) => item.id === metricId);

    if (!metric) {
      return;
    }

    metric.value = value;

    metric.trend.push({
      time: new Date().toISOString(),
      value,
    });

    if (metric.trend.length > 30) {
      metric.trend.shift();
    }
  };
}

export const simulatorStore = new SimulatorStore();
