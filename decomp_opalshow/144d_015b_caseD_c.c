
void __cdecl16far switchD_1000:6efd::caseD_c(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x3a);
  (*pcVar1)();
  return;
}

