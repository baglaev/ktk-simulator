import { Header } from '@/widgets/Header/ui/Header';
import { WarningInfo } from '@/widgets/WarningInfo/ui/WarningInfo';

interface Props {
  children?: React.ReactNode;
}

export const MainLayout = (props: Props) => {
  const { children } = props;

  return (
    <div>
      <Header />
      {children}
      <WarningInfo />
    </div>
  );
};

MainLayout.displayName = 'MainLayout';
