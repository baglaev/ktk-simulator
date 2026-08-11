import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { IconInfo } from '@consta/icons/IconInfo';

import styles from './SimulatorSummary.module.css';
import type { TaskExecutionItem } from '../../model/result.types';

interface Props {
  tasks: TaskExecutionItem[];
}

export const TasksDoneContainer = ({ tasks }: Props) => {
  return (
    <section className={styles.tasksDoneContainer}>
      <Text size="l" className={styles.title}>
        Выполнение задач
      </Text>

      <div className={styles.taskItemsContainer}>
        {tasks.map((task) => (
          <div key={task.taskId} className={styles.taskItem}>
            <div className={styles.taskName}>
              <IconInfo size="s" />

              <div>
                <Text>{task.title}</Text>

                <Text size="xs" view="secondary">
                  {task.description}
                </Text>
              </div>
            </div>

            <Badge
              label={
                task.status === 'success'
                  ? 'Выполнено'
                  : task.status === 'warning'
                    ? 'С замечанием'
                    : 'Не выполнено'
              }
              status={
                task.status === 'success'
                  ? 'success'
                  : task.status === 'warning'
                    ? 'warning'
                    : 'error'
              }
            />
          </div>
        ))}
      </div>
    </section>
  );
};
