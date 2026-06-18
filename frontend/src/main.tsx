import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import "./index.css";
import { queryClient } from "./lib/query";
import { router } from "./router";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipPrimitive.Provider delayDuration={150} skipDelayDuration={300}>
        <RouterProvider router={router} />
      </TooltipPrimitive.Provider>
    </QueryClientProvider>
  </React.StrictMode>,
);
