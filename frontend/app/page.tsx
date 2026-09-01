import { Dashboard } from "@/components/Dashboard";
import { AppLayout } from "@/components/layout/AppLayout";

export default function Home() {
  return (
    <AppLayout currentPage="overview">
      <Dashboard />
    </AppLayout>
  );
}

