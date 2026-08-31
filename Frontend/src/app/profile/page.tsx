"use client";

import { Camera, CheckCircle2, KeyRound, Loader2, Save, Trash2, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { AppShell } from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { ProfileAvatar } from "@/components/ProfileAvatar";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import * as authApi from "@/lib/api/auth";
import { useAuthStore } from "@/lib/store/auth-store";

const MAX_PROFILE_PICTURE_BYTES = 4 * 1024 * 1024;
const PROFILE_PICTURE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);

export default function ProfilePage() {
  const router = useRouter();
  const authenticated = useAuthStore((state) => state.authenticated);
  const hydrated = useAuthStore((state) => state.hydrated);
  const user = useAuthStore((state) => state.user);
  const setSession = useAuthStore((state) => state.setSession);
  const fileInput = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [picture, setPicture] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState<"details" | "password" | "picture" | null>(null);
  const [error, setError] = useState<unknown>();
  const [success, setSuccess] = useState<string | null>(null);

  /* Account data and local object URLs hydrate from external systems. */
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (hydrated && !authenticated) router.replace("/login");
  }, [authenticated, hydrated, router]);

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setEmail(user.email);
  }, [user]);

  useEffect(() => {
    if (!picture) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(picture);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [picture]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (!hydrated || !user) {
    return (
      <AppShell>
        <LoadingState title="Opening your profile" description="Restoring your account details securely." />
      </AppShell>
    );
  }

  async function saveDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setSuccess(null);
    const cleanedName = name.trim().replace(/\s+/g, " ");
    if (cleanedName.length < 2) return setError(new Error("Enter a name with at least 2 characters."));
    if (!email.includes("@")) return setError(new Error("Enter a valid email address."));

    setBusy("details");
    try {
      const updated = await authApi.updateProfile({ name: cleanedName, email: email.trim() });
      setSession(updated);
      setSuccess("Profile details updated.");
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  }

  async function savePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setSuccess(null);
    if (newPassword.length < 8) return setError(new Error("Your new password must be at least 8 characters."));
    if (newPassword !== confirmPassword) return setError(new Error("New password confirmation does not match."));

    setBusy("password");
    try {
      const result = await authApi.updatePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(result.message);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  }

  function choosePicture(file: File | null) {
    setError(undefined);
    setSuccess(null);
    if (!file) return setPicture(null);
    if (!PROFILE_PICTURE_TYPES.has(file.type)) {
      if (fileInput.current) fileInput.current.value = "";
      return setError(new Error("Choose a JPEG, PNG, WebP, or GIF image."));
    }
    if (file.size > MAX_PROFILE_PICTURE_BYTES) {
      if (fileInput.current) fileInput.current.value = "";
      return setError(new Error("Profile pictures must be 4 MB or smaller."));
    }
    setPicture(file);
  }

  async function uploadPicture() {
    if (!picture) return;
    setError(undefined);
    setSuccess(null);
    setBusy("picture");
    try {
      const updated = await authApi.uploadProfilePicture(picture);
      setSession(updated);
      setPicture(null);
      if (fileInput.current) fileInput.current.value = "";
      setSuccess("Profile picture updated.");
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  }

  async function removePicture() {
    setError(undefined);
    setSuccess(null);
    setBusy("picture");
    try {
      const updated = await authApi.deleteProfilePicture();
      setSession(updated);
      setPicture(null);
      if (fileInput.current) fileInput.current.value = "";
      setSuccess("Profile picture removed.");
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell>
      <div>
        <p className="text-xs font-extrabold tracking-[0.15em] text-[#d56535]">YOUR ACCOUNT</p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-[-0.03em] text-[#123c32] sm:text-5xl">Profile and security.</h1>
        <p className="mt-2 max-w-2xl text-[#60766f]">Keep your personal details, sign-in methods, and profile picture up to date.</p>
      </div>

      <div className="mt-7 grid gap-5 lg:grid-cols-[340px_1fr]">
        <section className="rounded-2xl border border-[#17453a]/10 bg-[#123c32] p-6 text-white shadow-[0_12px_40px_rgba(18,60,50,.12)]">
          <div className="flex flex-col items-center text-center">
            {previewUrl ? (
              // Local previews cannot use Next image optimization.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={previewUrl} alt="New profile picture preview" className="h-32 w-32 rounded-full object-cover ring-4 ring-white/15" />
            ) : (
              <ProfileAvatar user={user} className="h-32 w-32 text-4xl ring-4 ring-white/15" />
            )}
            <h2 className="mt-5 text-xl font-extrabold">{user.name}</h2>
            <p className="mt-1 text-sm text-[#c2d4cc]">{user.email}</p>
          </div>

          <div className="mt-6 grid gap-3 border-t border-white/10 pt-6">
            <label className="grid gap-2 text-sm font-bold text-[#dceae2]">
              <span>Choose a new picture</span>
              <input
                ref={fileInput}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                onChange={(event) => choosePicture(event.target.files?.[0] ?? null)}
                className="block w-full text-xs text-[#c2d4cc] file:mr-3 file:rounded-lg file:border-0 file:bg-white/10 file:px-3 file:py-2 file:font-bold file:text-white hover:file:bg-white/15"
              />
            </label>
            <p className="text-xs leading-5 text-[#9fb8ae]">JPEG, PNG, WebP, or GIF. Maximum 4 MB.</p>
            <Button type="button" disabled={!picture || busy !== null} onClick={uploadPicture} className="w-full bg-[#e36f3d] hover:bg-[#cb5f31]">
              {busy === "picture" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />} Save picture
            </Button>
            {user.profile_picture_version ? (
              <Button type="button" variant="ghost" disabled={busy !== null} onClick={removePicture} className="w-full text-[#f6c5b3] hover:bg-white/10 hover:text-white">
                <Trash2 className="h-4 w-4" /> Remove picture
              </Button>
            ) : null}
          </div>
        </section>

        <div className="grid content-start gap-5">
          {success ? (
            <div className="flex items-center gap-3 rounded-xl border border-[#b9d7c6] bg-[#eef8f1] p-4 text-sm font-bold text-[#246044]" role="status">
              <CheckCircle2 className="h-5 w-5" /> {success}
            </div>
          ) : null}
          <ApiErrorAlert error={error} />

          <form onSubmit={saveDetails} className="rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_8px_30px_rgba(18,60,50,.04)] sm:p-7">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#e6efe9] text-[#17453a]"><UserRound className="h-5 w-5" /></span>
              <div><h2 className="font-extrabold text-[#173e34]">Personal details</h2><p className="text-sm text-[#60766f]">Used to identify your saved trips and account.</p></div>
            </div>
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <Field label="Name"><input className={inputClass} value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" required /></Field>
              <Field label="Email address"><input className={inputClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></Field>
            </div>
            <Button type="submit" className="mt-6" disabled={busy !== null || (name === user.name && email === user.email)}>
              {busy === "details" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save details
            </Button>
          </form>

          {user.has_password ? (
            <form onSubmit={savePassword} className="rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_8px_30px_rgba(18,60,50,.04)] sm:p-7">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#fdf0e8] text-[#b5532e]"><KeyRound className="h-5 w-5" /></span>
                <div><h2 className="font-extrabold text-[#173e34]">Change password</h2><p className="text-sm text-[#60766f]">Confirm your current password before choosing a new one.</p></div>
              </div>
              <div className="mt-6 grid gap-5 md:grid-cols-3">
                <Field label="Current password"><input className={inputClass} type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" required /></Field>
                <Field label="New password"><input className={inputClass} type="password" minLength={8} maxLength={72} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" required /></Field>
                <Field label="Confirm new password"><input className={inputClass} type="password" minLength={8} maxLength={72} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" required /></Field>
              </div>
              <Button type="submit" className="mt-6" disabled={busy !== null || !currentPassword || !newPassword || !confirmPassword}>
                {busy === "password" ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />} Update password
              </Button>
            </form>
          ) : (
            <section className="rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_8px_30px_rgba(18,60,50,.04)] sm:p-7">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#e6efe9] text-[#17453a]"><KeyRound className="h-5 w-5" /></span>
                <div><h2 className="font-extrabold text-[#173e34]">Google sign-in</h2><p className="text-sm text-[#60766f]">This account does not have a password. Continue with the same Google account whenever you sign in.</p></div>
              </div>
            </section>
          )}
        </div>
      </div>
    </AppShell>
  );
}
