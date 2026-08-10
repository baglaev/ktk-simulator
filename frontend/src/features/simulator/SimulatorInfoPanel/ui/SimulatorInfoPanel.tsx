import { observer } from 'mobx-react-lite';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

import styles from './SimulatorInfoPanel.module.css';

import { Text } from '@consta/uikit/Text';

export const SimulatorInfoPanel = observer(() => {
  const { selectedComponent } = simulatorStore;

  if (!selectedComponent) {
    return <section className={styles.panel}>Выберите элемент схемы</section>;
  }

  return (
    <section className={styles.panel}>
      <Text size="l">{selectedComponent.tag}</Text>

      <Text size="s">{selectedComponent.name}</Text>

      {selectedComponent.parameters.map((parameter) => {
        const trend = simulatorStore.getParameterHistory(parameter.parameterId);

        return (
          <div key={parameter.parameterId}>
            <div>
              {parameter.name}: {Math.round(parameter.valuePercent)}%
            </div>

            <ResponsiveContainer width="100%" height={50}>
              <LineChart data={trend}>
                <Line dataKey="value" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </section>
  );
});

SimulatorInfoPanel.displayName = 'SimulatorInfoPanel';
