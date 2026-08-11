import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';

import styles from './SimulatorSummary.module.css';
import type { ResultRemark } from '../../model/result.types';

interface Props {
  remarks: ResultRemark[];
}

export const RecordedComments = ({ remarks }: Props) => {
  return (
    <section className={styles.recordedComments}>
      <Text size="l">Зафиксированные замечания</Text>

      {remarks.map((remark) => (
        <div key={remark.code} className={styles.commentsItem}>
          <Badge
            status={
              remark.status === 'success'
                ? 'success'
                : remark.status === 'warning'
                  ? 'warning'
                  : 'error'
            }
            size="xs"
            form="round"
          />

          <div>
            <Text weight="semibold">{remark.title}</Text>

            <Text size="s" view="secondary">
              {remark.description}
            </Text>
          </div>
        </div>
      ))}
    </section>
  );
};
