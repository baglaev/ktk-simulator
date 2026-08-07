import { Text } from '@consta/uikit/Text';
import styles from './SimulatorSummary.module.css';

export const ParametrsControlled = () => {
  return (
    <section>
      <Text size="2xl" className={styles.title}>
        Параметры управления
      </Text>
    </section>
  );
};

ParametrsControlled.displayName = 'ParametrsControlled';
