import { observer } from 'mobx-react-lite';

import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts';

import { Button } from '@consta/uikit/Button';
import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';

import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

import styles from './SimulatorInfoPanel.module.css';

export const SimulatorInfoPanel = observer(() => {
  const { selectedComponent } = simulatorStore;

  if (!selectedComponent) {
    return (
      <section className={styles.panel}>
        <Text size="m">Выберите элемент схемы</Text>
      </section>
    );
  }

  const isPump = selectedComponent.componentType === 'pump';

  const isRunning = selectedComponent.operatingState === 'running';

  const handleStartPump = () => {
    simulatorStore.sendAction('start_pump', selectedComponent.componentId);
  };

  const handleStopPump = () => {
    simulatorStore.sendAction('stop_pump', selectedComponent.componentId);
  };

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <Text size="xl" weight="semibold">
            {selectedComponent.tag}
          </Text>

          <Text size="s" view="secondary">
            {selectedComponent.name}
          </Text>
        </div>

        {isPump && (
          <div className={styles.operatingState}>
            <Badge
              status={isRunning ? 'success' : 'system'}
              label={isRunning ? 'Работает' : 'Остановлен'}
            />
          </div>
        )}
      </div>

      {isPump && (
        <div className={styles.passport}>
          <Text size="s" view="secondary">
            Параметры насоса
          </Text>

          <div className={styles.passportItems}>
            <div>
              <Text size="xs" view="secondary">
                Производительность
              </Text>

              <Text size="s">450 м³/ч</Text>
            </div>

            <div>
              <Text size="xs" view="secondary">
                Давление
              </Text>

              <Text size="s">19,5 кгс/см²</Text>
            </div>

            <div>
              <Text size="xs" view="secondary">
                Мощность
              </Text>

              <Text size="s">400 кВт</Text>
            </div>
          </div>
        </div>
      )}

      {selectedComponent.parameters.length > 0 && (
        <div className={styles.parameters}>
          <Text size="s" weight="semibold" className={styles.parametersTitle}>
            Диагностические параметры
          </Text>

          {selectedComponent.parameters.map((parameter) => {
            const history = simulatorStore.getParameterHistory(parameter.parameterId);

            return (
              <div key={parameter.parameterId} className={styles.parameter}>
                <div className={styles.parameterInfo}>
                  <div className={styles.parameterName}>
                    <Text size="s">{parameter.name}</Text>

                    <Badge
                      size="xs"
                      form="round"
                      status={
                        parameter.status === 'success'
                          ? 'success'
                          : parameter.status === 'warning'
                            ? 'warning'
                            : 'error'
                      }
                    />
                  </div>

                  <Text size="m" weight="semibold">
                    {Math.round(parameter.valuePercent)}%
                  </Text>
                </div>

                <div className={styles.chartContainer}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history}>
                      <YAxis hide domain={['dataMin', 'dataMax']} />

                      <Line
                        type="monotone"
                        dataKey="value"
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {isPump && !isRunning && selectedComponent.parameters.length === 0 && (
        <div className={styles.stopped}>
          <Text size="s" view="secondary">
            Насос остановлен. Диагностические параметры КОМПАКС не отображаются.
          </Text>
        </div>
      )}

      {isPump && (
        <div className={styles.actions}>
          {isRunning ? (
            <Button
              width="full"
              view="secondary"
              label="Вывести из работы"
              onClick={handleStopPump}
            />
          ) : (
            <Button width="full" view="primary" label="Ввести в работу" onClick={handleStartPump} />
          )}
        </div>
      )}
    </section>
  );
});

SimulatorInfoPanel.displayName = 'SimulatorInfoPanel';
