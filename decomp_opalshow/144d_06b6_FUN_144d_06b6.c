
void __cdecl16near FUN_144d_06b6(void)

{
  code *pcVar1;
  uint in_AX;
  uint uVar2;
  uint extraout_DX;
  int unaff_DS;
  bool bVar3;
  
  uVar2 = in_AX + *(uint *)0x342;
  if (!CARRY2(in_AX,*(uint *)0x342)) {
    if (*(uint *)0x33c < uVar2) {
      bVar3 = CARRY2((uint)(CONCAT12(0xfff0 < uVar2,uVar2 + 0xf) >> 1) >> 3,unaff_DS - *(int *)0x3b3
                    );
      pcVar1 = (code *)swi(0x21);
      (*pcVar1)();
      if (bVar3) goto LAB_144d_06f3;
      *(int *)0x33c = (uVar2 + 0xf & 0xfff0) - 1;
      in_AX = extraout_DX;
    }
    *(int *)0x342 = *(int *)0x342 + in_AX;
    return;
  }
LAB_144d_06f3:
  FUN_144d_03a6();
  return;
}

