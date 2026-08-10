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
    }
  };

  return (
    <div className={styles.simulatorSchema}>
      <div className={styles.schemeSvgContainer}>
        <SchemeSvg onClick={handleSchemeClick} className={styles.schemeSvg} />

        <div className={styles.valueContainer}>
          <div className={`${styles.valueItem} ${styles.pra}`}>
            <Text>PRA 351</Text>

            <div className={styles.procentContainer}>
              <Text size="m" weight="bold">
                {pra351 ? `${Math.round(pra351.valuePercent)}%` : '--'}
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

          <div className={`${styles.valueItem} ${styles.fyqr}`}>
            <Text>FYQR 117</Text>

            <div className={styles.procentContainer}>
              <Text size="m" weight="bold">
                {fyqr117 ? `${Math.round(fyqr117.valuePercent)}%` : '--'}
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
        </div>

        <div className={`${styles.valueItem} ${styles.lrca}`}>
          <Text>LRCA 605</Text>

          <div className={styles.procentContainer}>
            <Text size="m" weight="bold">
              {lrca605 ? `${Math.round(lrca605.valuePercent)}%` : '--'}
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
