import { Header } from '@/widgets/Header/ui/Header';
import { WarningInfo } from '@/widgets/WarningInfo/ui/WarningInfo';

interface Props {
  children?: React.ReactNode;

  userName?: string;
  userInfo?: string;

  showWarning?: boolean;
}

export const MainLayout = ({ children, userName, userInfo, showWarning = true }: Props) => {
  return (
    <div>
      <Header userName={userName} userInfo={userInfo} />

      {children}

      {showWarning && <WarningInfo />}
    </div>
  );
};
