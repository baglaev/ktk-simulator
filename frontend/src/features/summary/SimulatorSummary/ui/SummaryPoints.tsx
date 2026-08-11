import { IconWatchStroked } from '@consta/icons/IconWatchStroked';
import { IconInfoCircle } from '@consta/icons/IconInfoCircle';
import { IconProcessing } from '@consta/icons/IconProcessing';
import { Text } from '@consta/uikit/Text';

import styles from './SimulatorSummary.module.css';

interface Props {
  totalScore: number;
  maxScore: number;
  elapsedTimeMs: number;
  mode: 'training' | 'control';
}

const formatTime = (ms: number) => {
  const totalSeconds = Math.floor(ms / 1000);

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

export const SummaryPoints = ({ totalScore, maxScore, elapsedTimeMs, mode }: Props) => {
  return (
    <section className={styles.summaryPointsSection}>
      <div className={styles.summaryPointItem}>
        <IconProcessing className={styles.icon} size="l" />

        <Text className={styles.summaryPointTitle}>Итоговая оценка</Text>

        <Text className={styles.summaryPointValue} size="2xl">
          {totalScore}
          <span>/{maxScore}</span>
        </Text>
      </div>

      <div className={styles.summaryPointItem}>
        <IconWatchStroked className={styles.icon} size="l" />

        <Text className={styles.summaryPointTitle}>Время прохождения</Text>

        <Text className={styles.summaryPointValue} size="2xl">
          {formatTime(elapsedTimeMs)}
        </Text>
      </div>

      <div className={styles.summaryPointItem}>
        <IconInfoCircle className={styles.icon} size="l" />

        <Text className={styles.summaryPointTitle}>Режим</Text>

        <Text className={styles.summaryPointValue} size="2xl">
          {mode === 'training' ? 'Обучающий' : 'Контрольный'}
        </Text>
      </div>
    </section>
  );
};
