// import { observer } from 'mobx-react-lite';
// import { useState } from 'react';
// import { Select } from '@consta/uikit/Select';
// import { Line, LineChart, ResponsiveContainer } from 'recharts';
// import { Button } from '@consta/uikit/Button';
// import { Text } from '@consta/uikit/Text';
// import { Badge } from '@consta/uikit/Badge';
// import { Modal } from '@consta/uikit/Modal';
// import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

// import styles from './SimulatorInfoPanel.module.css';

// interface DiagnosisOption {
//   label: string;
//   value: string;
//   isCorrect: boolean;
// }

// type ConfirmAction = 'diagnosis' | 'startPump' | 'stopPump' | null;

// const diagnosisOptions: DiagnosisOption[] = [
//   {
//     label: 'Развивающийся износ подшипника',
//     value: 'bearing-wear',
//     isCorrect: true,
//   },
//   {
//     label: 'Кавитационный режим работы',
//     value: 'cavitation',
//     isCorrect: false,
//   },
//   {
//     label: 'Электрическая перегрузка двигателя',
//     value: 'motor-overload',
//     isCorrect: false,
//   },
//   {
//     label: 'Нарушение подачи на всасывающей линии',
//     value: 'suction-line',
//     isCorrect: false,
//   },
//   {
//     label: 'Неисправность датчика системы КОМПАКС',
//     value: 'kompaks-sensor',
//     isCorrect: false,
//   },
// ];

// export const SimulatorInfoPanel = observer(() => {
//   const { selectedComponent } = simulatorStore;

//   const [isDiagnosisOpen, setIsDiagnosisOpen] = useState(false);
//   const [selectedDiagnosis, setSelectedDiagnosis] = useState<DiagnosisOption | null>(null);
//   const [isDiagnosisSubmitted, setIsDiagnosisSubmitted] = useState(false);
//   const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
//   const [pendingDiagnosis, setPendingDiagnosis] = useState<DiagnosisOption | null>(null);

//   if (!selectedComponent) {
//     return (
//       <section className={styles.panel}>
//         <Text size="m">Выберите элемент схемы</Text>
//       </section>
//     );
//   }

//   const isPump = selectedComponent.componentType === 'pump';

//   const isHeatExchanger = selectedComponent.componentType === 'heat_exchanger';

//   const isRunning = selectedComponent.operatingState === 'running';

//   const handleStartPump = () => {
//     setConfirmAction('startPump');
//   };

//   const handleStopPump = () => {
//     setConfirmAction('stopPump');
//   };

//   const canRunDiagnostics = isPump && selectedComponent.uiId !== 'pump-h1v' && isRunning;

//   const handleDiagnosisChange = (diagnosis: DiagnosisOption | null) => {
//     if (!diagnosis || isDiagnosisSubmitted) {
//       return;
//     }

//     setPendingDiagnosis(diagnosis);
//     setConfirmAction('diagnosis');
//   };

//   const handleConfirm = () => {
//     if (confirmAction === 'diagnosis' && pendingDiagnosis) {
//       simulatorStore.sendAction('submit_diagnosis', selectedComponent.componentId, {
//         diagnosis: pendingDiagnosis.isCorrect ? '1' : '0',
//       });

//       setSelectedDiagnosis(pendingDiagnosis);
//       setIsDiagnosisSubmitted(true);
//       setPendingDiagnosis(null);
//     }

//     if (confirmAction === 'startPump') {
//       simulatorStore.sendAction('start_pump', selectedComponent.componentId);
//     }

//     if (confirmAction === 'stopPump') {
//       simulatorStore.sendAction('stop_pump', selectedComponent.componentId);
//     }

//     setConfirmAction(null);
//   };

//   const handleCancelConfirm = () => {
//     setConfirmAction(null);
//     setPendingDiagnosis(null);
//   };

//   const getConfirmTitle = () => {
//     switch (confirmAction) {
//       case 'diagnosis':
//         return 'Подтверждение диагноза';

//       case 'startPump':
//         return 'Ввод насоса в работу';

//       case 'stopPump':
//         return 'Остановка насоса';

//       default:
//         return '';
//     }
//   };

//   const getConfirmText = () => {
//     switch (confirmAction) {
//       case 'diagnosis':
//         return `Вы уверены, что хотите выбрать диагноз «${pendingDiagnosis?.label}»? После подтверждения изменить ответ будет нельзя.`;

//       case 'startPump':
//         return `Вы уверены, что хотите ввести насос ${selectedComponent.tag} в работу?`;

//       case 'stopPump':
//         return `Вы уверены, что хотите вывести насос ${selectedComponent.tag} из работы?`;

//       default:
//         return '';
//     }
//   };

//   return (
//     <section className={styles.panel}>
//       <div className={styles.header}>
//         <div>
//           <Text size="xl" weight="semibold">
//             {selectedComponent.tag}
//           </Text>

//           <Text size="s" view="secondary">
//             {selectedComponent.name}
//           </Text>
//         </div>

//         {isPump && (
//           <div className={styles.operatingState}>
//             <Badge
//               status={isRunning ? 'success' : 'system'}
//               label={isRunning ? 'Работает' : 'Остановлен'}
//             />
//           </div>
//         )}
//       </div>

//       {isPump && (
//         <div className={styles.passport}>
//           <Text size="s" view="secondary">
//             Параметры насоса
//           </Text>

//           <div className={styles.passportItems}>
//             <div>
//               <Text size="xs" view="secondary">
//                 Производительность
//               </Text>

//               <Text size="s">450 м³/ч</Text>
//             </div>

//             <div>
//               <Text size="xs" view="secondary">
//                 Давление
//               </Text>

//               <Text size="s">19,5 кгс/см²</Text>
//             </div>

//             <div>
//               <Text size="xs" view="secondary">
//                 Мощность
//               </Text>

//               <Text size="s">400 кВт</Text>
//             </div>
//           </div>
//         </div>
//       )}

//       {isHeatExchanger && selectedComponent.state && (
//         <div className={styles.details}>
//           <Text size="s" view="secondary" className={styles.detailsTitle}>
//             {selectedComponent.state.detailsTitle}
//           </Text>

//           <div className={styles.composition}>
//             {selectedComponent.state.composition?.map((item, index) => (
//               <div key={`${item}-${index}`} className={styles.compositionItem}>
//                 <Text size="s">{item}</Text>
//               </div>
//             ))}
//           </div>
//         </div>
//       )}

//       {selectedComponent.parameters.map((parameter) => {
//         const history = simulatorStore.getParameterHistory(parameter.parameterId);

//         return (
//           <div key={parameter.parameterId} className={styles.parameter}>
//             <div className={styles.parameterName}>
//               <Badge
//                 size="xs"
//                 form="round"
//                 status={
//                   parameter.status === 'success'
//                     ? 'success'
//                     : parameter.status === 'warning'
//                       ? 'warning'
//                       : 'error'
//                 }
//               />

//               <Text size="xs">{parameter.name}</Text>
//             </div>

//             <Text size="s" weight="semibold" className={styles.parameterValue}>
//               {parameter.value} {parameter.unit}
//             </Text>

//             <div className={styles.chartContainer}>
//               <ResponsiveContainer width="100%" height="100%">
//                 <LineChart
//                   data={history}
//                   margin={{
//                     top: 2,
//                     right: 2,
//                     bottom: 2,
//                     left: 2,
//                   }}
//                 >
//                   <Line
//                     type="monotone"
//                     dataKey="value"
//                     strokeWidth={2}
//                     dot={false}
//                     isAnimationActive={false}
//                   />
//                 </LineChart>
//               </ResponsiveContainer>
//             </div>
//           </div>
//         );
//       })}

//       {isPump && !isRunning && selectedComponent.parameters.length === 0 && (
//         <div className={styles.stopped}>
//           <Text size="s" view="secondary">
//             Насос остановлен. Диагностические параметры КОМПАКС не отображаются.
//           </Text>
//         </div>
//       )}

//       {isPump && (
//         <div className={styles.actions}>
//           {canRunDiagnostics && (
//             <>
//               {!isDiagnosisOpen ? (
//                 <Button
//                   width="full"
//                   view="secondary"
//                   label="Провести диагностику"
//                   onClick={() => setIsDiagnosisOpen(true)}
//                 />
//               ) : (
//                 <div>
//                   <Select
//                     placeholder="Выберите диагноз"
//                     items={diagnosisOptions}
//                     value={selectedDiagnosis}
//                     onChange={handleDiagnosisChange}
//                     getItemLabel={(item) => item.label}
//                     getItemKey={(item) => item.value}
//                     disabled={isDiagnosisSubmitted}
//                   />

//                   {isDiagnosisSubmitted && (
//                     <Text size="s" view="secondary">
//                       Ответ отправлен
//                     </Text>
//                   )}
//                 </div>
//               )}
//             </>
//           )}

//           {isRunning ? (
//             <Button
//               width="full"
//               view="secondary"
//               label="Вывести из работы"
//               onClick={handleStopPump}
//             />
//           ) : (
//             <Button width="full" view="primary" label="Ввести в работу" onClick={handleStartPump} />
//           )}
//         </div>
//       )}

//       <Modal
//         isOpen={confirmAction !== null}
//         hasOverlay
//         onClickOutside={handleCancelConfirm}
//         onEsc={handleCancelConfirm}
//         className={styles.confirmModal}
//       >
//         <div className={styles.confirmModalContent}>
//           <Text size="xl" weight="semibold">
//             {getConfirmTitle()}
//           </Text>

//           <Text size="m">{getConfirmText()}</Text>

//           <div className={styles.confirmModalActions}>
//             <Button label="Отмена" view="ghost" onClick={handleCancelConfirm} />

//             <Button label="Подтвердить" view="primary" onClick={handleConfirm} />
//           </div>
//         </div>
//       </Modal>
//     </section>
//   );
// });

// SimulatorInfoPanel.displayName = 'SimulatorInfoPanel';

import { observer } from 'mobx-react-lite';
import { useState } from 'react';

import { Select } from '@consta/uikit/Select';
import { Line, LineChart, ResponsiveContainer } from 'recharts';
import { Button } from '@consta/uikit/Button';
import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { Modal } from '@consta/uikit/Modal';

import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

import styles from './SimulatorInfoPanel.module.css';

interface DiagnosisOption {
  label: string;
  value: string;
  isCorrect: boolean;
}

type ConfirmAction = 'diagnosis' | 'startPump' | 'stopPump' | null;

const diagnosisOptions: DiagnosisOption[] = [
  {
    label: 'Развивающийся износ подшипника',
    value: 'bearing-wear',
    isCorrect: true,
  },
  {
    label: 'Кавитационный режим работы',
    value: 'cavitation',
    isCorrect: false,
  },
  {
    label: 'Электрическая перегрузка двигателя',
    value: 'motor-overload',
    isCorrect: false,
  },
  {
    label: 'Нарушение подачи на всасывающей линии',
    value: 'suction-line',
    isCorrect: false,
  },
  {
    label: 'Неисправность датчика системы КОМПАКС',
    value: 'kompaks-sensor',
    isCorrect: false,
  },
];

export const SimulatorInfoPanel = observer(() => {
  const { selectedComponent } = simulatorStore;

  const [isDiagnosisOpen, setIsDiagnosisOpen] = useState(false);

  const [selectedDiagnosis, setSelectedDiagnosis] = useState<DiagnosisOption | null>(null);

  const [isDiagnosisSubmitted, setIsDiagnosisSubmitted] = useState(false);

  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);

  const [pendingDiagnosis, setPendingDiagnosis] = useState<DiagnosisOption | null>(null);

  if (!selectedComponent) {
    return (
      <section className={styles.panel}>
        <Text size="m">Выберите элемент схемы</Text>
      </section>
    );
  }

  const isPump = selectedComponent.componentType === 'pump';

  const isRunning = selectedComponent.operatingState === 'running';

  const hasComposition = Boolean(selectedComponent.state?.composition?.length);

  const handleStartPump = () => {
    setConfirmAction('startPump');
  };

  const handleStopPump = () => {
    setConfirmAction('stopPump');
  };

  const canRunDiagnostics = selectedComponent.componentId === 'eq-n1a' && isRunning;

  const handleRunDiagnostics = () => {
    simulatorStore.sendAction('run_diagnostics', selectedComponent.componentId);
    setIsDiagnosisOpen(true);
  };

  const handleDiagnosisChange = (diagnosis: DiagnosisOption | null) => {
    if (!diagnosis || isDiagnosisSubmitted) {
      return;
    }

    setPendingDiagnosis(diagnosis);
    setConfirmAction('diagnosis');
  };

  const handleConfirm = () => {
    if (confirmAction === 'diagnosis' && pendingDiagnosis) {
      simulatorStore.sendAction('submit_diagnosis', selectedComponent.componentId, {
        diagnosis: pendingDiagnosis.isCorrect ? '1' : '0',
      });

      setSelectedDiagnosis(pendingDiagnosis);

      setIsDiagnosisSubmitted(true);
      setPendingDiagnosis(null);
    }

    if (confirmAction === 'startPump') {
      simulatorStore.sendAction('start_pump', selectedComponent.componentId);
    }

    if (confirmAction === 'stopPump') {
      simulatorStore.sendAction('stop_pump', selectedComponent.componentId);
    }

    setConfirmAction(null);
  };

  const handleCancelConfirm = () => {
    setConfirmAction(null);
    setPendingDiagnosis(null);
  };

  const getConfirmTitle = () => {
    switch (confirmAction) {
      case 'diagnosis':
        return 'Подтверждение диагноза';

      case 'startPump':
        return 'Ввод насоса в работу';

      case 'stopPump':
        return 'Остановка насоса';

      default:
        return '';
    }
  };

  const getConfirmText = () => {
    switch (confirmAction) {
      case 'diagnosis':
        return `Вы уверены, что хотите выбрать диагноз «${pendingDiagnosis?.label}»? После подтверждения изменить ответ будет нельзя.`;

      case 'startPump':
        return `Вы уверены, что хотите ввести насос ${selectedComponent.tag} в работу?`;

      case 'stopPump':
        return `Вы уверены, что хотите вывести насос ${selectedComponent.tag} из работы?`;

      default:
        return '';
    }
  };

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <Text size="xl" weight="semibold">
            {selectedComponent.tag}
          </Text>

          <Text size="s" view="secondary">
            {selectedComponent.name}
          </Text>
        </div>

        {isPump && (
          <div className={styles.operatingState}>
            <Badge
              status={isRunning ? 'success' : 'system'}
              label={isRunning ? 'Работает' : 'Остановлен'}
            />
          </div>
        )}
      </div>

      {isPump && (
        <div className={styles.passport}>
          <Text size="s" view="secondary">
            Параметры насоса
          </Text>

          <div className={styles.passportItems}>
            <div>
              <Text size="xs" view="secondary">
                Производительность
              </Text>

              <Text size="s">450 м³/ч</Text>
            </div>

            <div>
              <Text size="xs" view="secondary">
                Давление
              </Text>

              <Text size="s">19,5 кгс/см²</Text>
            </div>

            <div>
              <Text size="xs" view="secondary">
                Мощность
              </Text>

              <Text size="s">400 кВт</Text>
            </div>
          </div>
        </div>
      )}

      {hasComposition ? (
        <div className={styles.details}>
          <Text size="s" weight="semibold">
            {selectedComponent.state?.detailsTitle ?? 'Состав блока'}
          </Text>

          <div className={styles.composition}>
            {selectedComponent.state?.composition?.map((item, index) => (
              <div key={`${item}-${index}`} className={styles.compositionItem}>
                <Text size="s">{item}</Text>
              </div>
            ))}
          </div>
        </div>
      ) : (
        selectedComponent.parameters.map((parameter) => {
          const history = simulatorStore.getParameterHistory(parameter.parameterId);

          return (
            <div key={parameter.parameterId} className={styles.parameter}>
              <div className={styles.parameterName}>
                <Badge
                  size="xs"
                  form="round"
                  status={
                    parameter.status === 'success'
                      ? 'success'
                      : parameter.status === 'warning'
                        ? 'warning'
                        : 'error'
                  }
                />

                <Text size="xs">{parameter.name}</Text>
              </div>

              <Text size="s" weight="semibold" className={styles.parameterValue}>
                {parameter.value} {parameter.unit}
              </Text>

              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={history}
                    margin={{
                      top: 2,
                      right: 2,
                      bottom: 2,
                      left: 2,
                    }}
                  >
                    <Line
                      type="monotone"
                      dataKey="value"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          );
        })
      )}

      {isPump && !isRunning && selectedComponent.parameters.length === 0 && (
        <div className={styles.stopped}>
          <Text size="s" view="secondary">
            Насос остановлен. Диагностические параметры КОМПАКС не отображаются.
          </Text>
        </div>
      )}

      {isPump && (
        <div className={styles.actions}>
          {canRunDiagnostics && (
            <>
              {!isDiagnosisOpen ? (
                <Button
                  width="full"
                  view="secondary"
                  label="Провести диагностику"
                  onClick={handleRunDiagnostics}
                />
              ) : (
                <div>
                  <Select
                    placeholder="Выберите диагноз"
                    items={diagnosisOptions}
                    value={selectedDiagnosis}
                    onChange={handleDiagnosisChange}
                    getItemLabel={(item) => item.label}
                    getItemKey={(item) => item.value}
                    disabled={isDiagnosisSubmitted}
                  />

                  {isDiagnosisSubmitted && (
                    <Text size="s" view="secondary">
                      Ответ отправлен
                    </Text>
                  )}
                </div>
              )}
            </>
          )}

          {isRunning ? (
            <Button
              width="full"
              view="secondary"
              label="Вывести из работы"
              onClick={handleStopPump}
            />
          ) : (
            <Button width="full" view="primary" label="Ввести в работу" onClick={handleStartPump} />
          )}
        </div>
      )}

      <Modal
        isOpen={confirmAction !== null}
        hasOverlay
        onClickOutside={handleCancelConfirm}
        onEsc={handleCancelConfirm}
        className={styles.confirmModal}
      >
        <div className={styles.confirmModalContent}>
          <Text size="xl" weight="semibold">
            {getConfirmTitle()}
          </Text>

          <Text size="m">{getConfirmText()}</Text>

          <div className={styles.confirmModalActions}>
            <Button label="Отмена" view="ghost" onClick={handleCancelConfirm} />

            <Button label="Подтвердить" view="primary" onClick={handleConfirm} />
          </div>
        </div>
      </Modal>
    </section>
  );
});

SimulatorInfoPanel.displayName = 'SimulatorInfoPanel';
