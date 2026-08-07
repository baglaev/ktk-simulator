import { Text } from '@consta/uikit/Text';
import styles from './SimulatorSummary.module.css';

export const ParametrsControlled = () => {
  return (
    <section className={styles.parametrsControlledContainer}>
      <Text size="l" className={styles.title}>
        Контролируемые параметры
      </Text>
      <div className={styles.parametrsContainer}>
        <div className={styles.pametrItem}>
          <Text>PRA 351</Text>
          <Text view="success">Восстановлено</Text>
        </div>

        <div className={styles.pametrItem}>
          <Text>PRA 351</Text>
          <Text view="success">Восстановлено</Text>
        </div>

        <div className={styles.pametrItem}>
          <Text>PRA 351</Text>
          <Text view="success">Восстановлено</Text>
        </div>

        <div className={styles.pametrItem}>
          <Text>PRA 351</Text>
          <Text view="success">Восстановлено</Text>
        </div>
      </div>
    </section>
  );
};

ParametrsControlled.displayName = 'ParametrsControlled';
