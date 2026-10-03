import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/shell/AppShell";
import { LandingPage } from "@/pages/landing";
import { OverviewPage } from "@/pages/overview";
import { FindingsPage } from "@/pages/findings";
import { TunnelsPage } from "@/pages/tunnels";
import { ClaimsPage } from "@/pages/claims";
import { CoveragePage } from "@/pages/coverage";
import { ComponentGallery } from "@/pages/_gallery";

export const App: React.FC = () => {
  return (
    <Routes>
      {/* Landing page outside shell */}
      <Route path="/" element={<LandingPage />} />

      {/* Main app shell */}
      <Route path="/app" element={<AppShell />}>
        <Route index element={<Navigate to="/app/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="findings" element={<FindingsPage />} />
        <Route path="tunnels" element={<TunnelsPage />} />
        <Route path="claims" element={<ClaimsPage />} />
        <Route path="coverage" element={<CoveragePage />} />
      </Route>

      {/* Hidden review gallery */}
      <Route path="/__gallery" element={<ComponentGallery />} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
