import { Text } from '@consta/uikit/Text';
import { Table, type TableColumn } from '@consta/table/Table';

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

      {/* <Table columns={columns} rows={journal} /> */}

      <div className={styles.tableScroll}>
        <Table columns={columns} rows={journal} />
      </div>
    </section>
  );
});

SimulatorEventLog.displayName = 'SimulatorEventLog';
