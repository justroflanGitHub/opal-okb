
void __cdecl16near
FUN_1100_079f(undefined2 param_1,undefined2 *param_2,undefined2 param_3,undefined2 param_4,
             undefined2 param_5)

{
  undefined1 uVar1;
  code *pcVar2;
  uint *puVar3;
  int iVar4;
  int iVar5;
  uint *puVar6;
  uint *puVar7;
  undefined2 unaff_DS;
  
  FUN_1100_083e();
  if (*(byte *)0x2d6 < 3) {
    uRam0000007c = 0x2ba;
    uRam0000007e = unaff_DS;
  }
  else if (*(int *)0x2d7 == 0x13) {
    (*(code *)*(undefined2 *)0x30c)();
    uVar1 = *(undefined1 *)0x1007;
    puVar3 = (uint *)*(undefined4 *)0x1120;
    puVar6 = (uint *)puVar3;
    iVar4 = 8;
    do {
      iVar5 = 4;
      do {
        puVar7 = puVar6;
        *puVar7 = *puVar7 ^ CONCAT11(uVar1,uVar1);
        iVar5 = iVar5 + -1;
        puVar6 = puVar7 + 1;
      } while (iVar5 != 0);
      puVar6 = puVar7 + 0x9d;
      iVar4 = iVar4 + -1;
    } while (iVar4 != 0);
    return;
  }
  pcVar2 = (code *)swi(0x10);
  (*pcVar2)();
  if (*(byte *)0x2d6 < 3) {
    *param_2 = param_4;
    param_2[1] = param_5;
  }
  return;
}

