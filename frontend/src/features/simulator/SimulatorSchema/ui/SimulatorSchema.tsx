import SchemeSvg from '@/shared/assets/scheme.svg?react';
import { simulatorStore } from '../model/simulatorSchema.store';

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
    <div>
      <SchemeSvg onClick={handleSchemeClick} />
    </div>
  );
};

SimulatorSchema.displayName = 'SimulatorSchema';
