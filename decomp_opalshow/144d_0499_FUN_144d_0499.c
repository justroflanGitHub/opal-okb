
void __cdecl16far FUN_144d_0499(int param_1)

{
  code *pcVar1;
  int iVar2;
  undefined2 unaff_DS;
  
  FUN_144d_0530();
  FUN_144d_0530();
  if (*(int *)0x5c0 == -0x292a) {
    (*(code *)*(undefined2 *)0x5c6)();
  }
  FUN_144d_0530();
  FUN_144d_0530();
  iVar2 = FUN_144d_056e();
  if (((iVar2 != 0) && ((*(byte *)0x3e8 & 4) == 0)) && (param_1 == 0)) {
    param_1 = 0xff;
  }
  FUN_144d_0503();
  if ((*(byte *)0x3e8 & 4) != 0) {
    *(undefined1 *)0x3e8 = 0;
    return;
  }
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  if (*(int *)0x5d0 != 0) {
    (*(code *)*(undefined2 *)0x5ce)();
  }
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  if (*(char *)0x3e2 != '\0') {
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
  }
  return;
}

