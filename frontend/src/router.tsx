import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { RouteError } from "./components/RouteError";
import { CertificatePage } from "./features/borrowing-base/CertificatePage";
import { BriefingPage } from "./features/briefing/BriefingPage";
import { ComparePage } from "./features/compare/ComparePage";
import { FccrPage } from "./features/fccr/FccrPage";
import { OverviewPage } from "./features/overview/OverviewPage";
import { SetupPage } from "./features/setup/SetupPage";
import { VerificationPage } from "./features/verification/VerificationPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "briefing", element: <BriefingPage /> },
      { path: "verification", element: <VerificationPage /> },
      { path: "borrowing-base", element: <CertificatePage /> },
      { path: "fccr", element: <FccrPage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "setup", element: <SetupPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
