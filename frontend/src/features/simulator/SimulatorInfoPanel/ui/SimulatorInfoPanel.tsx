import { observer } from 'mobx-react-lite';
import { toJS } from 'mobx';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import styles from './SimulatorInfoPanel.module.css';
import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';
import { Text } from '@consta/uikit/Text';

export const SimulatorInfoPanel = observer(() => {
  const { selectedElementId, metrics } = simulatorStore;

  if (!selectedElementId) {
    return <section className={styles.panel}>Выберите элемент схемы</section>;
  }

  return (
    <section className={styles.panel}>
      <Text size="l">{selectedElementId}</Text>

      {toJS(metrics).map((metric) => (
        <div key={metric.id}>
          <div>
            {metric.title}: {metric.value} {metric.unit}
          </div>

          <ResponsiveContainer width="100%" height={50}>
            <LineChart data={metric.trend}>
              <Line dataKey="value" stroke={metric.color} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ))}
    </section>
  );
});

SimulatorInfoPanel.displayName = 'SimulatorInfoPanel';
