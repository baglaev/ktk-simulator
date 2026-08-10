import { Navigate, Outlet } from 'react-router-dom';
import { observer } from 'mobx-react-lite';
import { authStore, type UserRole } from '@/features/auth/model/auth.api.store';

interface Props {
  allowedRole: UserRole;
}

export const ProtectedRoute = observer((props: Props) => {
  const { allowedRole } = props;

  if (!authStore.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (authStore.role !== allowedRole) {
    if (authStore.role === 'instructor') {
      return <Navigate to="/instructor-page" replace />;
    }

    return <Navigate to="/" replace />;
  }

  return <Outlet />;
});
