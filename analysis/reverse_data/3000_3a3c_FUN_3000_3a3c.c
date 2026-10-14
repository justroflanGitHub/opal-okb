
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_3000_3a3c(void)

{
  char *pcVar1;
  code *pcVar2;
  byte bVar3;
  undefined2 uVar4;
  int iVar5;
  uint in_CX;
  int *piVar6;
  undefined1 *puVar7;
  undefined2 uVar8;
  undefined2 uVar9;
  undefined2 uVar10;
  undefined2 unaff_SS;
  int unaff_DS;
  undefined1 uVar11;
  char cVar12;
  char cVar13;
  int *in_stack_00000014;
  int *in_stack_00000018;
  int *in_stack_0000001c;
  undefined4 uVar14;
  
  puVar7 = &stack0xfffe;
  uVar14 = CONCAT22(*(undefined2 *)0x1946,*(int *)0x1944);
  uVar4 = *(undefined2 *)(*(int *)0x1944 + 2);
  *(undefined2 *)0x5e7c = 3;
  *(undefined2 *)0x5e88 = 2;
  uVar8 = (undefined2)((ulong)in_stack_00000018 >> 0x10);
  piVar6 = (int *)in_stack_00000018;
  if (*in_stack_00000018 == 0 && piVar6[1] == 0) {
    *(undefined2 *)0x5e7c = 2;
    *(undefined2 *)0x5e88 = 3;
  }
  uVar9 = (undefined2)((ulong)in_stack_00000014 >> 0x10);
  if ((*(int *)0x5e88 == 2) && (*in_stack_00000014 != 0 || ((int *)in_stack_00000014)[1] != 0)) {
    *(undefined2 *)0x5e88 = 3;
  }
  *(undefined2 *)0x5e82 = 3;
  *(undefined2 *)0x5e8a = 2;
  uVar10 = (undefined2)((ulong)in_stack_0000001c >> 0x10);
  if (*in_stack_0000001c == 0 && ((int *)in_stack_0000001c)[1] == 0) {
    *(undefined2 *)0x5e82 = 2;
    *(undefined2 *)0x5e8a = 3;
  }
  if ((*(int *)0x5e8a == 2) && (*in_stack_00000014 != 0 || ((int *)in_stack_00000014)[1] != 0)) {
    *(undefined2 *)0x5e8a = 3;
  }
  *(undefined2 *)0x5e98 = _FUN_4000_dff0;
  *(undefined2 *)0x5e9a = uRam0004dff2;
  *(undefined2 *)0x5e9c = uRam0004dff4;
  *(undefined2 *)0x5e9e = uRam0004dff6;
  if (*in_stack_0000001c == 0 && ((int *)in_stack_0000001c)[1] == 0) {
    pcVar2 = (code *)swi(0x39);
    (*pcVar2)();
    uVar9 = (undefined2)uVar14;
    pcVar2 = (code *)swi(0x38);
    (*pcVar2)();
    pcVar2 = (code *)swi(0x39);
    (*pcVar2)();
    uVar14 = CONCAT22(unaff_DS,uVar9);
    pcVar2 = (code *)swi(0x3d);
    (*pcVar2)();
  }
  pcVar2 = (code *)swi(0x3c);
  (*pcVar2)();
  pcVar2 = (code *)swi(0x35);
  (*pcVar2)(uVar14,uVar4);
  pcVar2 = (code *)swi(0x3d);
  (*pcVar2)();
  if (*in_stack_00000018 == 0 && piVar6[1] == 0) {
    pcVar2 = (code *)swi(0x35);
    (*pcVar2)();
    puVar7 = (undefined1 *)((uint)&stack0xfffe ^ in_CX);
    pcVar2 = (code *)swi(0x35);
    (*pcVar2)();
    pcVar2 = (code *)swi(0x3d);
    (*pcVar2)();
  }
  pcVar2 = (code *)swi(0x3c);
  (*pcVar2)();
  pcVar2 = (code *)swi(0x3c);
  (*pcVar2)();
  pcVar2 = (code *)swi(0x35);
  bVar3 = (*pcVar2)();
  pcVar1 = (char *)((int)piVar6 + unaff_DS);
  cVar13 = SBORROW1(*pcVar1,bVar3) != SBORROW1(*pcVar1 - bVar3,bVar3 < 0xdd);
  *pcVar1 = (*pcVar1 - bVar3) - (bVar3 < 0xdd);
  cVar12 = *pcVar1 < '\0';
  uVar11 = *pcVar1 == '\0';
  pcVar2 = (code *)swi(0x3c);
  (*pcVar2)();
  pcVar2 = (code *)swi(0x35);
  uVar4 = (*pcVar2)();
  if (!(bool)uVar11 && cVar13 == cVar12) {
    pcVar2 = (code *)swi(0x3d);
    (*pcVar2)();
    iVar5 = *(int *)((int)*(undefined4 *)(puVar7 + -0x16) + 2);
    *(int *)0x5e70 = iVar5;
    uVar4 = *(undefined2 *)(puVar7 + 0xc);
    iVar5 = (iVar5 * **(int **)(puVar7 + 6) + *(int *)(puVar7 + 10)) - *(int *)(puVar7 + -0x12);
    *(int *)(puVar7 + -0x10) = iVar5;
    *(undefined2 *)(puVar7 + -0xe) = uVar4;
    func_0x0002f5ce(0x1000,0xea0,iVar5,uVar4);
    return;
  }
  func_0x0002f5ce(0x1000,uVar4);
  return;
}

