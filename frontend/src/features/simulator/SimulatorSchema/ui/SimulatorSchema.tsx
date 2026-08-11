import SchemeSvg from '@/shared/assets/scheme.svg?react';
import { simulatorStore } from '../model/simulatorSchema.store';
import styles from './SimulatorSchema.module.css';
import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { observer } from 'mobx-react-lite';

export const SimulatorSchema = observer(() => {
  const { setSelectedElement, getParameter } = simulatorStore;

  const pra351 = getParameter('PRA351');
  const fyqr117 = getParameter('FYQR117');
  const lrca605 = getParameter('LRCA605');

  const clickableIds = [
    'pump-h1',
    'pump-h1a',
    'pump-h1b',
    'pump-h1v',
    'heat-exchanger-t1-t11',
    'elou-block',
    'e15',
  ];

  const handleSchemeClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const target = event.target as SVGElement;

    const element = target.closest('g[id]');

    if (!element) {
      return;
    }

    let id = element.id;

    if (id.startsWith('pump-shape')) {
      id = element.parentElement?.parentElement?.id ?? id;
    }

    if (clickableIds.includes(id)) {
      console.log('Нажат объект:', id);

      setSelectedElement(id);

      if (id === 'e15') {
        simulatorStore.sendAction('view_signal', 'LRCA605');
      }
    }
  };

  const handleSignalClick = (targetId: string) => {
    simulatorStore.sendAction('view_signal', targetId);
  };

  return (
    <div className={styles.simulatorSchema}>
      <div className={styles.schemeSvgContainer}>
        <SchemeSvg onClick={handleSchemeClick} className={styles.schemeSvg} />

        <div className={styles.valueContainer}>
          {/* <div className={`${styles.valueItem} ${styles.pra}`}>
            <Text>PRA 351</Text>

            <div className={styles.procentContainer}>
              <Text size="m" weight="bold">
                {pra351 ? `${pra351.value} ${pra351.unit}` : '--'}
              </Text>

              {pra351 && (
                <Badge
                  status={
                    pra351.status === 'success'
                      ? 'success'
                      : pra351.status === 'warning'
                        ? 'warning'
                        : 'error'
                  }
                  form="round"
                  size="xs"
                />
              )}
            </div>

            <Text size="xs">От исходного</Text>
          </div> */}

          <div
            className={`${styles.valueItem} ${styles.pra}`}
            onClick={() => handleSignalClick('PRA351')}
          >
            <Text>PRA 351</Text>

            <div className={styles.procentContainer}>
              <Text size="m" weight="bold">
                {pra351 ? `${pra351.value} ${pra351.unit}` : '--'}
              </Text>

              {pra351 && (
                <Badge
                  status={
                    pra351.status === 'success'
                      ? 'success'
                      : pra351.status === 'warning'
                        ? 'warning'
                        : 'error'
                  }
                  form="round"
                  size="xs"
                />
              )}
            </div>

            <Text size="xs">От исходного</Text>
          </div>

          <div
            className={`${styles.valueItem} ${styles.fyqr}`}
            onClick={() => handleSignalClick('FYQR117')}
          >
            <Text>FYQR 117</Text>

            <div className={styles.procentContainer}>
              <Text size="m" weight="bold">
                {fyqr117 ? `${fyqr117.value} ${fyqr117.unit}` : '--'}
              </Text>

              {fyqr117 && (
                <Badge
                  status={
                    fyqr117.status === 'success'
                      ? 'success'
                      : fyqr117.status === 'warning'
                        ? 'warning'
                        : 'error'
                  }
                  form="round"
                  size="xs"
                />
              )}
            </div>

            <Text size="xs">От исходного</Text>
          </div>

          {/* <div className={`${styles.valueItem} ${styles.fyqr}`}>
            <Text>FYQR 117</Text>

            <div className={styles.procentContainer}>
              <Text size="m" weight="bold">
                {fyqr117 ? `${fyqr117.value} ${fyqr117.unit}` : '--'}
              </Text>

              {fyqr117 && (
                <Badge
                  status={
                    fyqr117.status === 'success'
                      ? 'success'
                      : fyqr117.status === 'warning'
                        ? 'warning'
                        : 'error'
                  }
                  form="round"
                  size="xs"
                />
              )}
            </div>

            <Text size="xs">От исходного</Text>
          </div> */}
        </div>

        {/* <div className={`${styles.valueItem} ${styles.lrca}`}>
          <Text>LRCA 605</Text>

          <div className={styles.procentContainer}>
            <Text size="m" weight="bold">
              {lrca605 ? `${lrca605.value} ${lrca605.unit}` : '--'}
            </Text>

            {lrca605 && (
              <Badge
                status={
                  lrca605.status === 'success'
                    ? 'success'
                    : lrca605.status === 'warning'
                      ? 'warning'
                      : 'error'
                }
                form="round"
                size="xs"
              />
            )}
          </div>
        </div> */}

        <div
          className={`${styles.valueItem} ${styles.lrca}`}
          onClick={() => handleSignalClick('LRCA605')}
        >
          <Text>LRCA 605</Text>

          <div className={styles.procentContainer}>
            <Text size="m" weight="bold">
              {lrca605 ? `${lrca605.value} ${lrca605.unit}` : '--'}
            </Text>

            {lrca605 && (
              <Badge
                status={
                  lrca605.status === 'success'
                    ? 'success'
                    : lrca605.status === 'warning'
                      ? 'warning'
                      : 'error'
                }
                form="round"
                size="xs"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

SimulatorSchema.displayName = 'SimulatorSchema';
