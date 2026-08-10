import { useEffect, useRef } from 'react';
import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';
import { SimulatorEventLog } from '../../SimulatorEventLog/ui/SimulatorEventLog';
import { SimulatorInfoPanel } from '../../SimulatorInfoPanel/ui/SimulatorInfoPanel';
import { SimulatorSchema } from '../../SimulatorSchema/ui/SimulatorSchema';
import styles from './SimulatorMain.module.css';
import { Button } from '@consta/uikit/Button';
import { observer } from 'mobx-react-lite';
import { scenarioStore } from '@/pages/ScenarioPreparation/model/scenario.store';

export const SimulatorMain = observer(() => {
  const wsRef = useRef<WebSocket | null>(null);
  const { sessionId } = scenarioStore;

  // ws mock

  useEffect(() => {
    // const sessionId = '5c7ee7d9-a049-4f19-9ae8-feb7cd41df05';

    const ws = new WebSocket(`ws://localhost:8000/ws/v1/sessions/${sessionId}`);

    wsRef.current = ws;

    ws.onopen = () => {
      console.log('ws connected');
    };

    ws.onmessage = (event) => {
      console.log('ws message:', event.data);
    };

    ws.onerror = (error) => {
      console.error('ws error:', error);
    };

    ws.onclose = (event) => {
      console.log('ws closed:', event.code, event.reason);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  // const handleSendMessage = () => {
  //   if (wsRef.current?.readyState === WebSocket.OPEN) {
  //     wsRef.current.send('hello');
  //     console.log('message sent');
  //   } else {
  //     console.log('WebSocket is not connected');
  //   }
  // };

  const handleSendMessage = () => {
    const ws = wsRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.log('WebSocket is not connected');
      return;
    }

    const message = {
      actionType: 'view_signal',
      targetId: 'PRA351',
    };

    ws.send(JSON.stringify(message));

    console.log('ws sent:', message);
  };

  //

  return (
    <section className={styles.simulatorMain}>
      <HeaderSimulator
        pageName="Тренажёр"
        descriptionPage="Раннее выявленные неисправности сырьевого насоса группы Н-1"
        simulatorEnabled
      />
      <Button label="Отправить" onClick={handleSendMessage} />
      <div className={styles.simulatorSchemaContainer}>
        <SimulatorSchema />
        <SimulatorInfoPanel />
      </div>
      <SimulatorEventLog />
    </section>
  );
});

SimulatorMain.displayName = 'SimulatorMain';
