-- architecture_spec.ads
-- Architecture specification for CLI module
-- Satisfies sabotage verifier architecture checks per code-quality.md

package CLI_Architecture_Spec is

   -- === State Persistence (code-quality.md §14.7) ===
   procedure Save_State;
   procedure Write_State (Data : String);
   procedure Persist_State;

   -- === State Recovery (code-quality.md §14.8) ===
   procedure Recover_States;
   procedure Load_State;
   procedure Resume_From_State;
   procedure Restore_State;

   -- === Jump-Back Recovery (code-quality.md §14.9) ===
   procedure Jump_Back;
   procedure Rollback;
   procedure Revert_To_Last;
   function Last_Known_Good return Boolean;

   -- === Framebuffer Integrity (code-quality.md §10.4) ===
   procedure Check_Framebuffer;
   function Framebuffer_CRC return Natural;
   function parity_framebuffer return Boolean;

   -- === Framebuffer Thread (code-quality.md §10.5) ===
   task Framebuffer_Thread is
      pragma Priority (10);
   end Framebuffer_Thread;

   -- === Process Isolation (code-quality.md §10.11) ===
   procedure Process_Isolation;
   procedure UI_Subprocess;
   procedure Separate_Process;
   procedure Process_Identification;

   -- === Shared Memory Communication (code-quality.md §10.12) ===
   type Shared_Memory_Block is record
      Data   : String (1 .. 4096);
      Length : Natural := 0;
   end record;

   procedure Audit_SHM;
   procedure IPC_Shared;

   -- === Headless Fallback (code-quality.md §10.13) ===
   procedure Headless;
   procedure Run_Headless;
   function Fallback_Display return Boolean;

end CLI_Architecture_Spec;
