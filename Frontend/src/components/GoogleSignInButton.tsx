"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import * as authApi from "@/lib/api/auth";

type GoogleCredentialResponse = {
  credential: string;
};

type GoogleAccounts = {
  id: {
    initialize: (configuration: {
      client_id: string;
      callback: (response: GoogleCredentialResponse) => void;
    }) => void;
    renderButton: (
      parent: HTMLElement,
      options: {
        type: "standard";
        theme: "outline";
        size: "large";
        text: "signin_with" | "signup_with";
        shape: "rectangular";
        logo_alignment: "left";
        width: number;
      },
    ) => void;
    cancel: () => void;
  };
};

declare global {
  interface Window {
    google?: { accounts: GoogleAccounts };
  }
}

type Props = {
  mode: "login" | "register";
  disabled: boolean;
  onCredential: (credential: string) => void | Promise<void>;
  onError: (error: Error) => void;
};

export function GoogleSignInButton({ mode, disabled, onCredential, onError }: Props) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const credentialHandler = useRef(onCredential);
  const errorHandler = useRef(onError);
  const [clientId, setClientId] = useState<string | null>(null);
  const [scriptReady, setScriptReady] = useState(false);

  useEffect(() => {
    credentialHandler.current = onCredential;
    errorHandler.current = onError;
  }, [onCredential, onError]);

  useEffect(() => {
    let active = true;
    authApi.googleAuthConfig()
      .then((config) => {
        if (active && config.enabled && config.client_id) setClientId(config.client_id);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const parent = buttonRef.current;
    const google = window.google;
    if (!parent || !clientId || !scriptReady || !google) return;

    parent.replaceChildren();
    google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => {
        if (!response.credential) return errorHandler.current(new Error("Google did not return a sign-in credential."));
        void credentialHandler.current(response.credential);
      },
    });
    let renderedWidth = 0;
    const render = () => {
      const width = Math.max(200, Math.min(400, Math.floor(parent.getBoundingClientRect().width || 320)));
      if (width === renderedWidth) return;
      renderedWidth = width;
      parent.replaceChildren();
      google.accounts.id.renderButton(parent, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: mode === "login" ? "signin_with" : "signup_with",
        shape: "rectangular",
        logo_alignment: "left",
        width,
      });
    };
    render();
    const observer = new ResizeObserver(render);
    observer.observe(parent);

    return () => {
      observer.disconnect();
      parent.replaceChildren();
      google.accounts.id.cancel();
    };
  }, [clientId, mode, scriptReady]);

  if (!clientId) return null;

  return (
    <div className="mt-8 grid gap-5">
      <div className={disabled ? "pointer-events-none opacity-60" : undefined} aria-busy={disabled}>
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="afterInteractive"
          onReady={() => setScriptReady(true)}
          onError={() => errorHandler.current(new Error("Google sign-in could not load. Check your connection and try again."))}
        />
        <div className="flex min-h-11 w-full justify-center overflow-hidden" ref={buttonRef} />
      </div>
      <div className="flex items-center gap-3 text-xs font-bold tracking-[0.14em] text-[#8aa097]" aria-hidden="true">
        <span className="h-px flex-1 bg-[#17453a]/10" />
        OR USE EMAIL
        <span className="h-px flex-1 bg-[#17453a]/10" />
      </div>
    </div>
  );
}
