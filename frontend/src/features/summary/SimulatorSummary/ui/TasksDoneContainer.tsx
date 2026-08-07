import { Text } from '@consta/uikit/Text';
import styles from './SimulatorSummary.module.css';
import { IconInfo } from '@consta/icons/IconInfo';
import { Badge } from '@consta/uikit/Badge';

export const TasksDoneContainer = () => {
  return (
    <section className={styles.tasksDoneContainer}>
      <Text size="l" className={styles.title}>
        Выполнение задачи
      </Text>

      <div className={styles.taskItemsContainer}>
        <div className={styles.taskItem}>
          <div className={styles.taskName}>
            <IconInfo size="s" />
            <Text>Источник отклонения</Text>
          </div>
          <div className={styles.taskStatusContainer}>
            <Text>Н1-А, определенно верно</Text>
            <Badge status="success" size="xs" form="round" />
          </div>
        </div>

        <div className={styles.taskItem}>
          <div className={styles.taskName}>
            <IconInfo size="s" />
            <Text>Источник отклонения</Text>
          </div>
          <div className={styles.taskStatusContainer}>
            <Text>Н1-А, определенно верно</Text>
            <Badge status="success" size="xs" form="round" />
          </div>
        </div>

        <div className={styles.taskItem}>
          <div className={styles.taskName}>
            <IconInfo size="s" />
            <Text>Источник отклонения</Text>
          </div>
          <div className={styles.taskStatusContainer}>
            <Text>Н1-А, определенно верно</Text>
            <Badge status="success" size="xs" form="round" />
          </div>
        </div>
      </div>
    </section>
  );
};

TasksDoneContainer.displayName = 'TasksDoneContainer';
