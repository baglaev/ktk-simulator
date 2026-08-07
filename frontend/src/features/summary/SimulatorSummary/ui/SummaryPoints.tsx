import { IconWatchStroked } from '@consta/icons/IconWatchStroked';
import styles from './SimulatorSummary.module.css';
import { Text } from '@consta/uikit/Text';
import { IconInfoCircle } from '@consta/icons/IconInfoCircle';
import { IconProcessing } from '@consta/icons/IconProcessing';

export const SummaryPoints = () => {
  return (
    <section className={styles.summaryPointsSection}>
      <div className={styles.summaryPointItem}>
        <IconProcessing className={styles.icon} size="l" />
        <Text className={styles.summaryPointTitle}>Итоговая оценка</Text>
        <Text className={styles.summaryPointValue} size="2xl">
          86<span>/100</span>
        </Text>
      </div>

      <div className={styles.summaryPointItem}>
        <IconWatchStroked className={styles.icon} size="l" />
        <Text className={styles.summaryPointTitle}>Время прохождения</Text>
        <Text className={styles.summaryPointValue} size="2xl">
          01:42
        </Text>
      </div>

      <div className={styles.summaryPointItem}>
        <IconInfoCircle className={styles.icon} size="l" />
        <Text className={styles.summaryPointTitle}>Режим</Text>
        <Text className={styles.summaryPointValue} size="2xl">
          Обучающий
        </Text>
      </div>
    </section>
  );
};

SummaryPoints.displayName = 'SummaryPoints';
