import { Header } from '@/widgets/Header/ui/Header';

interface Props {
  children?: React.ReactNode;
}

export const MainLayout = (props: Props) => {
  const { children } = props;

  return (
    <div>
      <Header />
      {children}
    </div>
  );
};

MainLayout.displayName = 'MainLayout';
