import { useEffect, useRef } from 'react';
import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';
import { SimulatorEventLog } from '../../SimulatorEventLog/ui/SimulatorEventLog';
import { SimulatorInfoPanel } from '../../SimulatorInfoPanel/ui/SimulatorInfoPanel';
import { SimulatorSchema } from '../../SimulatorSchema/ui/SimulatorSchema';
import styles from './SimulatorMain.module.css';
import { Button } from '@consta/uikit/Button';

export const SimulatorMain = () => {
  const wsRef = useRef<WebSocket | null>(null);

  // ws mock

  useEffect(() => {
    const sessionId = '526a8b08-31b9-4234-9678-d0f2f5eaed34';

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
  }, []);

  const handleSendMessage = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('hello');
      console.log('message sent');
    } else {
      console.log('WebSocket is not connected');
    }
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
};

SimulatorMain.displayName = 'SimulatorMain';
