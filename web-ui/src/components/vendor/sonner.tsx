import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group font-mono"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-surface-raised group-[.toaster]:text-text-primary group-[.toaster]:border-border-hairline group-[.toaster]:shadow-lg font-mono text-xs",
          description: "group-[.toast]:text-text-secondary",
          actionButton:
            "group-[.toast]:bg-signal group-[.toast]:text-black font-semibold",
          cancelButton:
            "group-[.toast]:bg-surface-panel group-[.toast]:text-text-secondary",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
