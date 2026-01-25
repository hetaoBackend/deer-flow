"use client";

import type { ChatStatus } from "ai";
import {
  CheckIcon,
  GraduationCapIcon,
  LightbulbIcon,
  ZapIcon,
} from "lucide-react";
import { useCallback, useMemo, useState, type ComponentProps } from "react";

import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import {
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import { useModels } from "@/core/models/hooks";
import type { AgentThreadContext } from "@/core/threads";
import { cn } from "@/lib/utils";

import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "../ai-elements/model-selector";

export function InputBox({
  className,
  disabled,
  autoFocus,
  status = "ready",
  context,
  extraHeader,
  isNewThread,
  onContextChange,
  onSubmit,
  onStop,
  ...props
}: Omit<ComponentProps<typeof PromptInput>, "onSubmit"> & {
  assistantId?: string | null;
  status?: ChatStatus;
  disabled?: boolean;
  context: Omit<AgentThreadContext, "thread_id">;
  extraHeader?: React.ReactNode;
  isNewThread?: boolean;
  onContextChange?: (context: Omit<AgentThreadContext, "thread_id">) => void;
  onSubmit?: (message: PromptInputMessage) => void;
  onStop?: () => void;
}) {
  const { t } = useI18n();
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const { models } = useModels();
  const selectedModel = useMemo(
    () => models.find((m) => m.name === context.model_name),
    [context.model_name, models],
  );
  const supportThinking = useMemo(
    () => selectedModel?.supports_thinking ?? false,
    [selectedModel],
  );
  const mode = useMemo(() => {
    if (context.is_plan_mode) {
      return "pro";
    }
    if (context.thinking_enabled) {
      return "thinking";
    }
    return "flash";
  }, [context.thinking_enabled, context.is_plan_mode]);
  const handleModelSelect = useCallback(
    (model_name: string) => {
      const supports_thinking = selectedModel?.supports_thinking ?? false;
      onContextChange?.({
        ...context,
        model_name,
        thinking_enabled: supports_thinking && context.thinking_enabled,
      });
      setModelDialogOpen(false);
    },
    [selectedModel?.supports_thinking, onContextChange, context],
  );
  const handleModeSelect = useCallback(
    (mode: "flash" | "thinking" | "pro") => {
      if (mode === "flash") {
        onContextChange?.({
          ...context,
          thinking_enabled: false,
          is_plan_mode: false,
        });
      } else if (mode === "thinking") {
        onContextChange?.({
          ...context,
          thinking_enabled: true,
          is_plan_mode: false,
        });
      } else if (mode === "pro") {
        onContextChange?.({
          ...context,
          thinking_enabled: true,
          is_plan_mode: true,
        });
      }
    },
    [onContextChange, context],
  );
  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      if (status === "streaming") {
        onStop?.();
        return;
      }
      if (!message.text) {
        return;
      }
      onSubmit?.(message);
    },
    [onSubmit, onStop, status],
  );
  return (
    <PromptInput
      className={cn(
        "bg-background/85 rounded-2xl backdrop-blur-sm transition-all duration-300 ease-out *:data-[slot='input-group']:rounded-2xl",
        className,
      )}
      disabled={disabled}
      globalDrop
      multiple
      onSubmit={handleSubmit}
      {...props}
    >
      {extraHeader && (
        <div className="absolute top-0 right-0 left-0 z-10">
          <div className="absolute right-0 bottom-0 left-0 flex items-center justify-center">
            {extraHeader}
          </div>
        </div>
      )}
      <PromptInputAttachments>
        {(attachment) => <PromptInputAttachment data={attachment} />}
      </PromptInputAttachments>
      <PromptInputBody className="absolute top-0 right-0 left-0 z-3">
        <PromptInputTextarea
          className={cn("size-full")}
          disabled={disabled}
          placeholder={t.inputBox.placeholder}
          autoFocus={autoFocus}
        />
      </PromptInputBody>
      <PromptInputFooter className="flex">
        <PromptInputTools>
          <PromptInputActionMenu>
            <PromptInputActionMenuTrigger />
            <PromptInputActionMenuContent className="w-80">
              <PromptInputActionAddAttachments
                label={t.inputBox.addAttachments}
              />
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuLabel className="text-muted-foreground text-xs">
                  {t.inputBox.mode}
                </DropdownMenuLabel>
                <PromptInputActionMenu>
                  <PromptInputActionMenuItem
                    className={cn(
                      mode === "flash"
                        ? "text-accent-foreground"
                        : "text-muted-foreground/65",
                    )}
                    onSelect={() => handleModeSelect("flash")}
                  >
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-1 font-bold">
                        <ZapIcon
                          className={cn(
                            "mr-2 size-4",
                            mode === "flash" && "text-accent-foreground",
                          )}
                        />
                        {t.inputBox.flashMode}
                      </div>
                      <div className="pl-7 text-xs">
                        {t.inputBox.flashModeDescription}
                      </div>
                    </div>
                    {mode === "flash" ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </PromptInputActionMenuItem>
                  {supportThinking && (
                    <PromptInputActionMenuItem
                      className={cn(
                        mode === "thinking"
                          ? "text-accent-foreground"
                          : "text-muted-foreground/65",
                      )}
                      onSelect={() => handleModeSelect("thinking")}
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-1 font-bold">
                          <LightbulbIcon
                            className={cn(
                              "mr-2 size-4",
                              mode === "thinking" && "text-accent-foreground",
                            )}
                          />
                          {t.inputBox.reasoningMode}
                        </div>
                        <div className="pl-7 text-xs">
                          {t.inputBox.reasoningModeDescription}
                        </div>
                      </div>
                      {mode === "thinking" ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </PromptInputActionMenuItem>
                  )}
                  <PromptInputActionMenuItem
                    className={cn(
                      mode === "pro"
                        ? "text-accent-foreground"
                        : "text-muted-foreground/65",
                    )}
                    onSelect={() => handleModeSelect("pro")}
                  >
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-1 font-bold">
                        <GraduationCapIcon
                          className={cn(
                            "mr-2 size-4",
                            mode === "pro" && "text-accent-foreground",
                          )}
                        />
                        {t.inputBox.proMode}
                      </div>
                      <div className="pl-7 text-xs">
                        {t.inputBox.proModeDescription}
                      </div>
                    </div>
                    {mode === "pro" ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </PromptInputActionMenuItem>
                </PromptInputActionMenu>
              </DropdownMenuGroup>
            </PromptInputActionMenuContent>
          </PromptInputActionMenu>
        </PromptInputTools>
        <PromptInputTools>
          <ModelSelector
            open={modelDialogOpen}
            onOpenChange={setModelDialogOpen}
          >
            <ModelSelectorTrigger asChild>
              <PromptInputButton>
                <ModelSelectorName className="text-xs font-normal">
                  {selectedModel?.display_name}
                </ModelSelectorName>
              </PromptInputButton>
            </ModelSelectorTrigger>
            <ModelSelectorContent>
              <ModelSelectorInput placeholder={t.inputBox.searchModels} />
              <ModelSelectorList>
                {models.map((m) => (
                  <ModelSelectorItem
                    key={m.name}
                    value={m.name}
                    onSelect={() => handleModelSelect(m.name)}
                  >
                    <ModelSelectorName>{m.display_name}</ModelSelectorName>
                    {m.name === context.model_name ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </ModelSelectorItem>
                ))}
              </ModelSelectorList>
            </ModelSelectorContent>
          </ModelSelector>
          <PromptInputSubmit
            className="rounded-full"
            disabled={disabled}
            variant="outline"
            status={status}
          />
        </PromptInputTools>
      </PromptInputFooter>
      {!isNewThread && (
        <div className="bg-background absolute right-0 -bottom-[17px] left-0 z-0 h-4"></div>
      )}
    </PromptInput>
  );
}
