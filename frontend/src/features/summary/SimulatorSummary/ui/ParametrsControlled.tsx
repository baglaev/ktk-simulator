import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';

import styles from './SimulatorSummary.module.css';
import type { ControlledParameter } from '../../model/result.types';

interface Props {
  parameters: ControlledParameter[];
}

export const ParametrsControlled = ({ parameters }: Props) => {
  return (
    <section className={styles.parametrsControlledContainer}>
      <Text size="l" className={styles.title}>
        Контролируемые параметры
      </Text>

      <div className={styles.parametrsContainer}>
        {parameters.map((parameter) => (
          <div key={parameter.parameterId} className={styles.pametrItem}>
            <div>
              <Text size="s">{parameter.name}</Text>

              <Text size="xs" view="secondary">
                {parameter.parameterId}
              </Text>
            </div>

            <div className={styles.parameterResult}>
              <Text weight="semibold">
                {parameter.finalValue} {parameter.unit}
              </Text>

              <Badge
                form="round"
                size="xs"
                status={
                  parameter.status === 'success'
                    ? 'success'
                    : parameter.status === 'warning'
                      ? 'warning'
                      : 'error'
                }
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
