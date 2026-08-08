import { Text } from '@consta/uikit/Text';
import { Table, type TableColumn } from '@consta/table/Table';
import styles from './SimulatorEventLog.module.css';

type Row = { time: string; description: string };

export const SimulatorEventLog = () => {
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

  const rows: Row[] = [
    {
      time: '00:01',
      description: 'Сценарий запущен',
    },
    {
      time: '00:04',
      description: 'Выбран обучающий режим',
    },
  ];

  return (
    <section className={styles.eventLog}>
      <Text className={styles.titleComments} size="l">
        Журнал событий
      </Text>
      <Table columns={columns} rows={rows} />
    </section>
  );
};

SimulatorEventLog.displayName = 'SimulatorEventLog';
