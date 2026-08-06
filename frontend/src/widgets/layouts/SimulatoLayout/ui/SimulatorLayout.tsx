interface Props {
  children?: React.ReactNode;
}

export const SimulatorLayout = (props: Props) => {
  const { children } = props;

  return <div>{children}</div>;
};

SimulatorLayout.displayName = 'SimulatorLayout';
