import { Text } from '@consta/uikit/Text';
import styles from './SimulatorSummary.module.css';
import { Badge } from '@consta/uikit/Badge';

export const RecordedComments = () => {
  return (
    <section className={styles.recordedComments}>
      <Text>Зафиксированные замечания</Text>
      <div className={styles.commentsItem}>
        <Badge status="warning" size="xs" form="round" />
        <Text>Позднее начало диагностики</Text>
      </div>

      <div className={styles.commentsItem}>
        <Badge status="warning" size="xs" form="round" />
        <Text>Позднее начало диагностики</Text>
      </div>
    </section>
  );
};

RecordedComments.displayName = 'RecordedComments';
