import SchemeSvg from '@/shared/assets/scheme.svg?react';
import { simulatorStore } from '../model/simulatorSchema.store';
import styles from './SimulatorSchema.module.css';
// import { Text } from '@consta/uikit/Text';

export const SimulatorSchema = () => {
  const { setSelectedElement } = simulatorStore;

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
      {/* <div className={styles.schemaNamingComponents}>
        <Text className={styles.itemF}>1. Ёмкости сырья</Text>
        <Text>2. Насосная группа Н-1</Text>
        <Text>3. Параметры на линии</Text>
        <Text>4. Теплообменный блок Т-1-Т-11</Text>
        <Text>5. Блок ЭЛОУ</Text>
        <Text>6. Е-15</Text>
      </div> */}
      <SchemeSvg onClick={handleSchemeClick} />
    </div>
  );
};

SimulatorSchema.displayName = 'SimulatorSchema';
