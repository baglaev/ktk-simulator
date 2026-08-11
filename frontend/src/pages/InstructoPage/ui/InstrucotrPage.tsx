import { useEffect, useState } from 'react';

import { observer } from 'mobx-react-lite';

import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { Loader } from '@consta/uikit/Loader';

import { IconArrowDown } from '@consta/icons/IconArrowDown';

import { Header } from '@/widgets/Header/ui/Header';

import { instructorStore } from '@/features/instructor/model/instructor.store';

import type { InstructorResultItem } from '@/features/instructor/model/instructor.types';

import styles from './InstructorPage.module.css';

const getModeName = (mode: InstructorResultItem['mode']) => {
  return mode === 'training' ? 'Обучающий' : 'Контрольный';
};

const formatDate = (date: string) => {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
};

const formatTime = (ms: number) => {
  const seconds = Math.floor(ms / 1000);

  const minutes = Math.floor(seconds / 60);

  const restSeconds = seconds % 60;

  return `${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`;
};

export const InstructorPage = observer(() => {
  const { results, total, isLoading, error, fetchResults } = instructorStore;

  const [openedSessionId, setOpenedSessionId] = useState<string | null>(null);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  if (isLoading) {
    return (
      <main className={styles.page}>
        <Header userName="Инструктор" userInfo="Инструктор" />

        <div className={styles.loaderContainer}>
          <Loader />
        </div>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <Header userName="Инструктор" userInfo="Инструктор" />

      <div className={styles.content}>
        <div className={styles.pageHeader}>
          <div>
            <Text size="2xl" weight="semibold">
              Результаты обучаемых
            </Text>

            <Text view="secondary" className={styles.pageDescription}>
              Результаты прохождения сценариев и журнал действий
            </Text>
          </div>

          <Badge label={`Всего прохождений: ${total}`} view="stroked" />
        </div>

        {error && <Text view="alert">{error}</Text>}

        <div className={styles.results}>
          {results.map((result) => {
            const isOpen = openedSessionId === result.sessionId;

            const isFailed =
              result.resultStatus === 'failed' || result.outcome === 'failed';
            const statusLabel = isFailed
              ? 'Не пройден'
              : result.resultStatus === 'passed_with_remarks'
                ? 'С замечаниями'
                : 'Пройден';

            return (
              <section key={result.sessionId} className={styles.resultCard}>
                <div className={styles.resultMainInfo}>
                  <div className={styles.traineeContainer}>
                    <Text size="m" weight="semibold">
                      {result.traineeName}
                    </Text>

                    <Text size="xs" view="secondary">
                      {formatDate(result.completedAt)}
                    </Text>
                  </div>

                  <div className={styles.infoItem}>
                    <Text size="xs" view="secondary">
                      Режим
                    </Text>

                    <Badge
                      label={getModeName(result.mode)}
                      view="stroked"
                      status={result.mode === 'training' ? 'normal' : 'system'}
                    />
                  </div>

                  <div className={styles.infoItem}>
                    <Text size="xs" view="secondary">
                      Время
                    </Text>

                    <Text weight="semibold">{formatTime(result.elapsedTimeMs)}</Text>
                  </div>

                  <div className={styles.infoItem}>
                    <Text size="xs" view="secondary">
                      Балл
                    </Text>

                    <Text size="xl" weight="semibold" view={isFailed ? 'alert' : 'success'}>
                      {result.totalScore}
                      <span className={styles.maxScore}>/{result.maxScore}</span>
                    </Text>
                  </div>

                  <div className={styles.infoItem}>
                    <Text size="xs" view="secondary">
                      Статус
                    </Text>

                    <Badge
                      label={statusLabel}
                      status={isFailed ? 'error' : 'success'}
                    />
                  </div>
                </div>

                <button
                  type="button"
                  className={styles.journalButton}
                  onClick={() => setOpenedSessionId(isOpen ? null : result.sessionId)}
                >
                  <div className={styles.journalButtonTitle}>
                    <Text size="s" weight="semibold">
                      Журнал прохождения
                    </Text>

                    <Text size="xs" view="secondary">
                      {result.journal.length} событий
                    </Text>
                  </div>

                  <IconArrowDown size="s" className={isOpen ? styles.arrowOpen : styles.arrow} />
                </button>

                {isOpen && (
                  <div className={styles.journalContainer}>
                    {result.journal.length === 0 ? (
                      <Text size="s" view="secondary">
                        В журнале нет событий
                      </Text>
                    ) : (
                      result.journal.map((journalItem, index) => (
                        <div
                          key={`${result.sessionId}-${journalItem.virtualTimeMs}-${index}`}
                          className={styles.journalItem}
                        >
                          <Text size="xs" view="secondary" className={styles.journalTime}>
                            {journalItem.time}
                          </Text>

                          <Badge
                            size="xs"
                            label={journalItem.kind === 'hint' ? 'Подсказка' : 'Действие'}
                            status={journalItem.kind === 'hint' ? 'warning' : 'normal'}
                          />

                          <Text size="s">{journalItem.description}</Text>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </main>
  );
});

InstructorPage.displayName = 'InstructorPage';
