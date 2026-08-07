import { observer } from 'mobx-react-lite';
import { toJS } from 'mobx';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

import styles from './SimulatorInfoPanel.module.css';
import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

export const SimulatorInfoPanel = observer(() => {
  const { selectedElementId, chartData } = simulatorStore;

  if (!selectedElementId) {
    return <section className={styles.panel}>Выберите элемент схемы</section>;
  }

  return (
    <section className={styles.panel}>
      <h3>{selectedElementId}</h3>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={toJS(chartData)}>
          <CartesianGrid />

          <XAxis dataKey="time" />

          <YAxis />

          <Tooltip />

          <Line type="monotone" dataKey="value" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
});

SimulatorInfoPanel.displayName = 'SimulatorInfoPanel';
