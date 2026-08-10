import { Navigate, Outlet } from 'react-router-dom';
import { observer } from 'mobx-react-lite';
import { authStore } from '@/features/auth/model/auth.api.store';
import type { UserRole } from '@/features/auth/model/auth.api';

interface Props {
  allowedRole: UserRole;
}

export const ProtectedRoute = observer(({ allowedRole }: Props) => {
  if (!authStore.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (authStore.role !== allowedRole) {
    return <Navigate to={authStore.role === 'instructor' ? '/instructor' : '/'} replace />;
  }

  return <Outlet />;
});
