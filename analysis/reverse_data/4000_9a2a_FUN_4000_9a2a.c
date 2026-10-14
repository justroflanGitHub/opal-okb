
void __cdecl16far FUN_4000_9a2a(void)

{
  int iVar1;
  int iVar2;
  int iVar3;
  undefined2 unaff_DS;
  undefined1 in_CF;
  undefined1 in_ZF;
  int *in_stack_0000000c;
  
  FUN_4000_9ce8();
  if (!(bool)in_ZF) {
    FUN_4000_9f88();
    if ((bool)in_CF) {
      iVar2 = *(int *)0x6316;
      iVar3 = *(int *)0x6318;
      FUN_4000_9f88();
      if ((bool)in_CF) {
        iVar1 = iVar2;
        if (iVar2 < *(int *)0x6316) {
          LOCK();
          iVar1 = *(int *)0x6316;
          *(int *)0x6316 = iVar2;
          UNLOCK();
        }
        iVar2 = iVar3;
        if (iVar3 < *(int *)0x6318) {
          LOCK();
          iVar2 = *(int *)0x6318;
          *(int *)0x6318 = iVar3;
          UNLOCK();
        }
        iVar3 = (iVar2 - *(int *)0x6318) + 1;
        iVar2 = *(int *)0x6316;
        (*(code *)*(undefined2 *)0x1522)();
        *in_stack_0000000c = ((iVar1 - iVar2) + 1) * (uint)*(byte *)0x1513;
        ((int *)in_stack_0000000c)[1] = iVar3;
        FUN_4000_abc4();
        do {
          FUN_4000_ac1f();
          (*(code *)*(undefined2 *)0x152c)();
          iVar3 = iVar3 + -1;
        } while (iVar3 != 0);
      }
    }
  }
  FUN_4000_9d04();
  return;
}

