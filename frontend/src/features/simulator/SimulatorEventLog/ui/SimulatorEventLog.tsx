import { Text } from '@consta/uikit/Text';
import { Table, type TableColumn } from '@consta/table/Table';
import { useEffect, useRef } from 'react';
import { observer } from 'mobx-react-lite';

import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

import styles from './SimulatorEventLog.module.css';

type Row = {
  entryId: string;
  time: string;
  description: string;
};

export const SimulatorEventLog = observer(() => {
  const { journal } = simulatorStore;

  const tableScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = tableScrollRef.current;

    if (!container) {
      return;
    }

    requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      });
    });
  }, [journal.length]);

  const columns: TableColumn<Row>[] = [
    {
      title: 'Время события',
      accessor: 'time',
      width: 100,
    },
    {
      title: 'Описание события',
      accessor: 'description',
    },
  ];

  return (
    <section className={styles.eventLog}>
      <Text className={styles.titleComments} size="l">
        Журнал событий
      </Text>

      <div ref={tableScrollRef} className={styles.tableScroll}>
        <Table columns={columns} rows={journal} />
      </div>
    </section>
  );
});

SimulatorEventLog.displayName = 'SimulatorEventLog';
